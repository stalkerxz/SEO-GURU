import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import boto3
import psycopg2
import redis

from ai_seo_service import (
    analyze_full_video_intelligence,
    analyze_opening_frames_with_ai,
    analyze_video_frames_with_ai,
    generate_seo_packages,
    transcribe_audio_with_openai,
)
from audio_analysis import analyze_audio_technical, extract_audio_track, no_audio_analysis
from seo_mock_generator import build_video_angle
from video_intelligence import build_retention_analysis, safe_confidence
from video_sampling import build_sampling_plan
from video_temporal_analysis import build_temporal_analysis, detect_scene_changes

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://video:video@localhost:5432/video_seo')
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', '/app/storage')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'videos')

r = redis.from_url(REDIS_URL)


def ffprobe_json(file_path: str):
    cmd = ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', file_path]
    return json.loads(subprocess.check_output(cmd).decode('utf-8'))


def extract_frames_at_timestamps(file_path: str, out_dir: str, timestamps: list[float]):
    extracted = []
    warnings = []
    for index, timestamp in enumerate(timestamps, start=1):
        output_path = Path(out_dir) / f'frame_{index:04d}.jpg'
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', f'{timestamp:.3f}',
            '-i', file_path, '-frames:v', '1', '-q:v', '2', '-y', str(output_path),
        ]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as exc:
            warnings.append(f'Frame extraction failed at {timestamp:.2f}s: ffmpeg exit {exc.returncode}.')
            continue
        if output_path.exists():
            extracted.append((output_path, timestamp))
    return extracted, warnings


def upload_frame(s3, frame_path: Path, job_id: str, idx: int, approx_time_sec: float):
    key = f'frames/{job_id}/frame_{idx:04d}.jpg'
    s3.upload_file(str(frame_path), MINIO_BUCKET, key)
    return {
        'index': idx,
        'storageKey': key,
        'filename': frame_path.name,
        'approxTimeSec': approx_time_sec,
        'previewUrl': f'/api/frames/{job_id}/{frame_path.name}'
    }


def persist_local_frame(frame_path: Path, job_id: str, idx: int, approx_time_sec: float):
    rel_key = f'frames/{job_id}/frame_{idx:04d}.jpg'
    target = Path(LOCAL_STORAGE_PATH) / rel_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(frame_path.read_bytes())
    return {
        'index': idx,
        'storageKey': rel_key,
        'filename': frame_path.name,
        'approxTimeSec': approx_time_sec,
        'previewUrl': f'/api/frames/{job_id}/{frame_path.name}'
    }


def build_analysis_report(duration, width, height, fps, has_audio, bitrate, frames, user_context):
    short_side = min(width, height) if width and height else 0
    is_vertical = bool(width and height and height > width)
    is_horizontal = bool(width and height and width > height)
    aspect_ratio = f"{width}:{height}" if width and height else None
    detected_issues = []
    recommendations = []
    niche = user_context.get('niche', 'general_video')
    goal = user_context.get('userGoal', 'views_and_reach')

    shorts_score = 50
    reels_score = 50
    tiktok_score = 50
    youtube_score = 50

    if is_vertical and duration <= 180:
        shorts_score += 25
        reels_score += 25
        tiktok_score += 25
    if is_horizontal:
        youtube_score += 30

    if duration < 5:
        detected_issues.append('Слишком короткое видео (менее 5 секунд).')
        recommendations.append('Увеличьте длительность хотя бы до 10–15 секунд для лучшего вовлечения.')
        shorts_score -= 20
        reels_score -= 20
        tiktok_score -= 20

    if duration > 180:
        detected_issues.append('Длительность более 180 секунд — хуже для коротких платформ.')
        recommendations.append('Подготовьте отдельную короткую версию до 60–180 секунд.')
        shorts_score -= 30
        reels_score -= 30
        tiktok_score -= 30

    if not has_audio:
        detected_issues.append('В видео не обнаружена аудиодорожка.')
        recommendations.append('Добавьте речь, музыку или звуковые эффекты для удержания внимания.')
        shorts_score -= 10
        reels_score -= 10
        tiktok_score -= 10
        youtube_score -= 10

    if short_side and short_side < 720:
        detected_issues.append('Низкое качество: короткая сторона меньше 720px.')
        recommendations.append('Экспортируйте видео минимум в HD (720p), лучше в Full HD (1080p).')
        shorts_score -= 15
        reels_score -= 15
        tiktok_score -= 15
        youtube_score -= 15

    if is_vertical and width and height and abs(width - 1080) <= 120 and abs(height - 1920) <= 160:
        shorts_score += 20
        reels_score += 20
        tiktok_score += 20

    if is_horizontal and duration <= 180:
        detected_issues.append('Горизонтальный формат ограничивает эффективность Shorts/Reels/TikTok.')
        recommendations.append('Сделайте вертикальную адаптацию 9:16 для коротких платформ.')
    if niche == 'auto' and duration <= 30:
        recommendations.extend([
            'Добавьте сильный текстовый хук в первые 0.5 секунды (например: DRIFT MODE / BMW X5).',
            'Используйте самый читаемый кадр как обложку (контрастный авто-ракурс, 2–4 слова на обложке).',
            'Для TikTok/Reels держите монтаж в диапазоне 12–18 секунд.',
            'Для YouTube обычного видео подготовьте отдельную длинную версию или публикуйте как Shorts.'
        ])
        if goal == 'views_and_reach':
            recommendations.append('Добавьте CTA-вопрос в закреплённый комментарий для роста обсуждения.')

    shorts_score = max(0, min(100, shorts_score))
    reels_score = max(0, min(100, reels_score))
    tiktok_score = max(0, min(100, tiktok_score))
    youtube_score = max(0, min(100, youtube_score))

    summary = 'Базовый технический анализ завершен. Подготовлен черновик платформенной оценки и SEO-структура.'
    technical_summary = {
        'durationSec': duration,
        'resolution': f'{width}x{height}' if width and height else None,
        'fps': fps,
        'aspectRatio': aspect_ratio,
        'hasAudio': has_audio,
        'bitrate': bitrate
    }
    content_hints = _build_content_hints(user_context, technical_summary)
    orientation = _orientation(width, height)
    if orientation == 'vertical' and duration <= 180:
        platform_primary_hint = 'shorts_reels_tiktok'
    elif orientation == 'horizontal' and duration > 60:
        platform_primary_hint = 'youtube_video'
    else:
        platform_primary_hint = 'needs_adaptation'
    if len(frames) <= 2:
        visual_rhythm_hint = 'static_or_low_sample'
    elif duration > 60:
        visual_rhythm_hint = 'extended_story'
    elif duration <= 30 and len(frames) >= 3:
        visual_rhythm_hint = 'short_dynamic'
    else:
        visual_rhythm_hint = 'mixed'
    video_fingerprint = {
        'durationBucket': _duration_bucket(duration),
        'orientation': orientation,
        'resolutionClass': _resolution_class(width, height),
        'hasAudio': has_audio,
        'frameCount': len(frames),
        'frameTimes': [frame.get('approxTimeSec', 0) for frame in frames],
        'filenameTokens': (user_context.get('extractedFilenameHints', {}) or {}).get('tokens', []),
        'detectedModel': (user_context.get('extractedFilenameHints', {}) or {}).get('detectedModel', ''),
        'contentHints': content_hints,
        'visualRhythmHint': visual_rhythm_hint,
        'platformPrimaryHint': platform_primary_hint
    }
    ai_meta = {
        'niche': niche,
        'keywords': user_context.get('keywords', []),
        'content_hints': content_hints,
        'video_fingerprint': video_fingerprint,
        'platform_fit': {
            'youtubeShorts': shorts_score,
            'youtubeVideo': youtube_score,
            'instagramReels': reels_score,
            'tiktok': tiktok_score
        },
        'original_filename': user_context.get('originalFilename', ''),
        'filename_hints': user_context.get('extractedFilenameHints', {}),
        'technical': technical_summary
    }
    video_angle = build_video_angle(ai_meta)
    generation_basis = _generation_basis(user_context, video_fingerprint)

    return {
        'summary': summary,
        'technical': technical_summary,
        'platformFit': {
            'youtubeShorts': {'score': shorts_score, 'notes': 'Оценка пригодности для YouTube Shorts.'},
            'youtubeVideo': {'score': youtube_score, 'notes': 'Оценка пригодности для классического YouTube-видео.'},
            'instagramReels': {'score': reels_score, 'notes': 'Оценка пригодности для Instagram Reels.'},
            'tiktok': {'score': tiktok_score, 'notes': 'Оценка пригодности для TikTok.'}
        },
        'detectedIssues': detected_issues,
        'recommendations': recommendations,
        'ai_input': {
            'technicalSummary': technical_summary,
            'frameSummary': {
                'totalFrames': len(frames),
                'frames': [
                    {
                        'index': frame.get('index'),
                        'approxTimeSec': frame.get('approxTimeSec'),
                        'previewUrl': frame.get('previewUrl')
                    }
                    for frame in frames
                ]
            },
            'frameManifest': {'totalFrames': len(frames), 'frames': frames},
            'videoFingerprint': video_fingerprint,
            'contentHints': content_hints,
            'platformFit': {
                'youtubeShorts': shorts_score,
                'youtubeVideo': youtube_score,
                'instagramReels': reels_score,
                'tiktok': tiktok_score
            },
            'videoAngle': video_angle,
            'generationBasis': generation_basis,
            'detectedIssues': detected_issues,
            'recommendations': recommendations,
            'userGoal': user_context.get('userGoal', 'views_and_reach'),
            'niche': user_context.get('niche', 'general_video'),
            'language': user_context.get('language', 'ru'),
            'geo': user_context.get('geo', ''),
            'brandName': user_context.get('brandName', ''),
            'keywords': user_context.get('keywords', [])
        },
    }




def _default_user_context():
    return {
        'userGoal': 'views_and_reach',
        'niche': 'general_video',
        'language': 'ru',
        'geo': '',
        'brandName': '',
        'keywords': [],
    }


def _extract_filename_hints(original_filename: str) -> dict:
    lowered = (original_filename or '').lower()
    tokens = [x for x in re.split(r'[^a-zа-я0-9]+', lowered, flags=re.IGNORECASE) if x]
    model = ''
    if 'bmw' in tokens:
        for candidate in ('x3', 'x5'):
            if candidate in tokens:
                model = f'BMW {candidate.upper()}'
                break
    return {'tokens': tokens[:12], 'detectedModel': model}


def _duration_bucket(duration: float) -> str:
    if duration < 10:
        return 'ultra_short'
    if duration <= 30:
        return 'short'
    if duration <= 180:
        return 'medium'
    return 'long'


def _orientation(width: int, height: int) -> str:
    if not width or not height:
        return 'unknown'
    if height > width:
        return 'vertical'
    if width > height:
        return 'horizontal'
    return 'square'


def _resolution_class(width: int, height: int) -> str:
    short_side = min(width, height) if width and height else 0
    long_side = max(width, height) if width and height else 0
    if short_side < 720:
        return 'low'
    if short_side < 1080:
        return 'hd'
    if long_side >= 3840 or short_side >= 2160:
        return 'ultra_hd'
    return 'full_hd'


def _build_content_hints(user_context: dict, technical_summary: dict) -> list[str]:
    filename = str(user_context.get('originalFilename', '') or '')
    keywords = user_context.get('keywords', []) if isinstance(user_context.get('keywords', []), list) else []
    extracted_tokens = (user_context.get('extractedFilenameHints', {}) or {}).get('tokens', [])
    source_chunks = [filename, ' '.join(keywords), ' '.join(extracted_tokens), json.dumps(technical_summary, ensure_ascii=False)]
    text = ' '.join(source_chunks).lower()
    auto_signal_text = ' '.join([filename, ' '.join(keywords), ' '.join(extracted_tokens)]).lower()
    niche = str(user_context.get('niche', 'general_video')).lower()
    auto_brands_models = [
        'bmw', 'mercedes', 'audi', 'toyota', 'kia', 'porsche', 'x3', 'x5', 'tesla', 'lexus', 'honda', 'hyundai'
    ]
    travel_terms = [
        'travel', 'trip', 'vacation', 'maldives', 'мальдивы', 'турция', 'турецкие', 'море', 'пляж', 'отель',
        'курорт', 'отдых', 'путешествие'
    ]
    resort_terms = ['море', 'пляж', 'maldives', 'мальдивы', 'курорт', 'отель', 'resort', 'beach', 'sea']

    hints: list[str] = []
    has_auto_model = any(term in auto_signal_text for term in auto_brands_models)
    has_auto_core = any(term in text for term in ['auto', 'авто', 'car', 'cars', 'detailing', 'wheel', 'wheels', 'кузов'])
    if has_auto_model or (niche == 'auto' and (has_auto_core or 'drift' in text or 'дрифт' in text)):
        hints.append('auto_model')

    if 'drift' in text or 'дрифт' in text:
        hints.append('drift')
    if 'phonk' in text or 'фонк' in text:
        hints.append('phonk_music')
    if 'cinematic' in text or 'синематик' in text:
        hints.append('cinematic_style')
    if any(term in text for term in ['night', 'ноч', 'lights']):
        hints.append('night_scene')
    if any(term in text for term in ['city', 'город', 'urban']):
        hints.append('city_scene')
    if any(term in text for term in ['interior', 'салон']):
        hints.append('interior')
    if any(term in text for term in ['review', 'обзор']):
        hints.append('review')
    if any(term in text for term in ['sale', 'продажа', 'for sale']):
        hints.append('sale_video')

    has_travel = niche == 'travel' or any(term in text for term in travel_terms)
    if has_travel:
        hints.append('travel_scene')
        hints.append('destination_video')
    if any(term in text for term in resort_terms):
        hints.append('resort_or_beach')
        if 'travel_scene' not in hints:
            hints.append('travel_scene')
        if 'destination_video' not in hints:
            hints.append('destination_video')
    if niche == 'travel' and 'auto_model' in hints and not has_auto_model:
        hints = [hint for hint in hints if hint != 'auto_model']
    return hints




def _generation_basis(user_context: dict, video_fingerprint: dict) -> list[str]:
    basis = ['technical_fingerprint']
    filename_tokens = (user_context.get('extractedFilenameHints', {}) or {}).get('tokens', [])
    if user_context.get('originalFilename') or filename_tokens:
        basis.append('filename_hints')
    if user_context.get('keywords'):
        basis.append('user_keywords')
    if len(basis) > 1:
        basis.append('mixed_context')
    return basis

def get_job_context(job_id: str):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('SELECT user_context, filename FROM video_jobs WHERE id=%s', (job_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    default_context = _default_user_context()
    if not row:
        return default_context

    raw = row[0] if row[0] else {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    keywords = raw.get('keywords', [])
    if isinstance(keywords, str):
        keywords = [x.strip() for x in keywords.split(',') if x.strip()]
    elif not isinstance(keywords, list):
        keywords = []

    context = {
        'userGoal': raw.get('userGoal') or default_context['userGoal'],
        'niche': raw.get('niche') or default_context['niche'],
        'language': raw.get('language') or default_context['language'],
        'geo': raw.get('geo') or '',
        'brandName': raw.get('brandName') or '',
        'keywords': [str(x).strip() for x in keywords if str(x).strip()],
    }
    original_filename = row[1] or ''
    context['originalFilename'] = original_filename
    context['extractedFilenameHints'] = _extract_filename_hints(original_filename)
    return context
def analyze_file(file_path: str, job_id: str, user_context):
    meta = ffprobe_json(file_path)
    vstream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'video'), {})
    astream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'audio'), None)
    duration = float(meta.get('format', {}).get('duration', 0) or 0)
    width = vstream.get('width', 0)
    height = vstream.get('height', 0)

    pipeline_warnings = []
    scene_detection_failed = False
    try:
        scene_candidates = detect_scene_changes(file_path)
    except Exception as exc:
        scene_candidates = []
        scene_detection_failed = True
        pipeline_warnings.append(f'Scene detection failed; using uniform sampling: {exc}')

    temporal_analysis = build_temporal_analysis(duration, scene_candidates)
    sampling_plan = build_sampling_plan(
        duration,
        scene_candidates,
        scene_detection_failed=scene_detection_failed,
    )

    with tempfile.TemporaryDirectory() as frame_dir:
        extracted_frames, extraction_warnings = extract_frames_at_timestamps(
            file_path,
            frame_dir,
            sampling_plan.get('selectedTimestampsSec', []),
        )
        pipeline_warnings.extend(extraction_warnings)
        frames = []
        if STORAGE_MODE == 'minio':
            s3 = boto3.client(
                's3',
                endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
                aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minio'),
                aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minio123')
            )
            for i, (frame_path, timestamp) in enumerate(extracted_frames, start=1):
                frames.append(upload_frame(s3, frame_path, job_id, i, round(timestamp, 3)))
        else:
            for i, (frame_path, timestamp) in enumerate(extracted_frames, start=1):
                frames.append(persist_local_frame(frame_path, job_id, i, round(timestamp, 3)))

    analysis_report = build_analysis_report(
        duration=duration,
        width=width,
        height=height,
        fps=vstream.get('r_frame_rate'),
        has_audio=astream is not None,
        bitrate=meta.get('format', {}).get('bit_rate'),
        frames=frames,
        user_context=user_context,
    )
    analysis_report['ai_input']['originalFilename'] = user_context.get('originalFilename', '')
    analysis_report['ai_input']['extractedFilenameHints'] = user_context.get('extractedFilenameHints', {})
    analysis_report['samplingPlan'] = sampling_plan
    analysis_report['temporalAnalysis'] = temporal_analysis
    analysis_report['ai_input']['samplingPlan'] = sampling_plan
    analysis_report['ai_input']['temporalAnalysis'] = temporal_analysis

    try:
        audio_analysis = analyze_audio_technical(file_path, astream, duration)
    except Exception as exc:
        audio_analysis = no_audio_analysis(duration) if astream is None else {
            'hasAudio': True,
            'durationSec': round(duration, 3),
            'codec': astream.get('codec_name'),
            'channels': astream.get('channels'),
            'sampleRate': None,
            'silenceRatio': None,
            'approximateLoudness': None,
            'speechPresent': None,
            'transcriptionStatus': 'not_attempted',
        }
        pipeline_warnings.append(f'Audio technical analysis failed: {exc}')

    transcript = {
        'status': 'no_audio' if astream is None else 'not_requested',
        'language': '',
        'text': '',
        'segments': [],
    }
    transcription_attempted = False
    if (
        astream is not None
        and os.getenv('AI_PROVIDER', 'mock').lower().strip() == 'openai'
        and os.getenv('OPENAI_API_KEY', '').strip()
    ):
        transcription_attempted = True
        try:
            with tempfile.TemporaryDirectory() as audio_dir:
                audio_path = extract_audio_track(file_path, audio_dir)
                transcript = transcribe_audio_with_openai(
                    audio_path,
                    str(user_context.get('language', '') or ''),
                )
        except Exception as exc:
            transcript = {'status': 'failed', 'language': '', 'text': '', 'segments': []}
            pipeline_warnings.append(f'Audio extraction/transcription failed: {exc}')
        transcription_warning = transcript.pop('_warning', None)
        if transcription_warning:
            pipeline_warnings.append(transcription_warning)

    audio_analysis['speechPresent'] = bool(transcript.get('text')) if transcript.get('status') in {'completed', 'empty'} else audio_analysis.get('speechPresent')
    audio_analysis['transcriptionStatus'] = transcript.get('status', 'not_requested')
    analysis_report['audioAnalysis'] = audio_analysis
    analysis_report['transcript'] = transcript
    analysis_report['ai_input']['audioAnalysis'] = audio_analysis
    analysis_report['ai_input']['transcript'] = transcript
    print(
        '[worker][context]',
        json.dumps({
            'job_id': job_id,
            'user_context': {
                'userGoal': user_context.get('userGoal', ''),
                'niche': user_context.get('niche', ''),
                'language': user_context.get('language', ''),
                'geo': user_context.get('geo', ''),
                'brandName': user_context.get('brandName', ''),
                'keywords': user_context.get('keywords', []),
                'originalFilename': user_context.get('originalFilename', ''),
                'extractedFilenameHints': user_context.get('extractedFilenameHints', {})
            },
            'ai_input': {
                'userGoal': analysis_report['ai_input'].get('userGoal', ''),
                'niche': analysis_report['ai_input'].get('niche', ''),
                'language': analysis_report['ai_input'].get('language', ''),
                'geo': analysis_report['ai_input'].get('geo', ''),
                'brandName': analysis_report['ai_input'].get('brandName', ''),
                'keywords': analysis_report['ai_input'].get('keywords', []),
                'originalFilename': analysis_report['ai_input'].get('originalFilename', ''),
                'extractedFilenameHints': analysis_report['ai_input'].get('extractedFilenameHints', {})
            }
        }, ensure_ascii=False)
    )

    ai_warnings = list(pipeline_warnings)
    visual_frames_sent = 0
    try:
        visual_analysis = analyze_video_frames_with_ai(
            analysis_report.get('ai_input', {}),
            analysis_report.get('ai_input', {}).get('frameManifest', {}),
        )
        visual_frames_sent = int(visual_analysis.get('_readableFrames', 0) or 0)
        if visual_analysis.get('_status') == 'skipped_no_readable_frames':
            ai_warnings.append('Visual AI analysis skipped: no readable frames.')
            analysis_report['ai_input']['analysisBasis'] = 'mock_heuristics'
        elif visual_analysis.get('_status') == 'invalid_response':
            ai_warnings.append('Visual AI analysis skipped: invalid model response.')
            analysis_report['ai_input']['analysisBasis'] = 'mock_heuristics'
        elif visual_analysis:
            visual_analysis.pop('_status', None)
            visual_analysis.pop('_readableFrames', None)
            analysis_report['ai_input']['visualAnalysis'] = visual_analysis
            visual_is_authoritative = safe_confidence(visual_analysis.get('confidence')) >= 0.5
            analysis_report['ai_input']['analysisBasis'] = (
                'visual_ai' if visual_is_authoritative else 'visual_ai_low_confidence'
            )
            meta_for_angle = {
                'niche': analysis_report['ai_input'].get('niche', 'general_video'),
                'keywords': analysis_report['ai_input'].get('keywords', []),
                'technical': analysis_report['ai_input'].get('technicalSummary', {}),
                'video_fingerprint': analysis_report['ai_input'].get('videoFingerprint', {}),
                'content_hints': analysis_report['ai_input'].get('contentHints', []),
                'filename_hints': analysis_report['ai_input'].get('extractedFilenameHints', {}),
                'original_filename': analysis_report['ai_input'].get('originalFilename', ''),
                'visual_analysis': visual_analysis,
            }
            analysis_report['ai_input']['videoAngle'] = build_video_angle(meta_for_angle)
            if visual_is_authoritative:
                analysis_report['ai_input']['generationBasis'] = [
                    'visual_ai',
                    'technical_fingerprint',
                    'user_context',
                ]
        else:
            analysis_report['ai_input']['analysisBasis'] = 'mock_heuristics'
    except Exception as exc:
        ai_warnings.append(f'Visual AI analysis failed, fallback to mock heuristics: {exc}')
        analysis_report['ai_input']['analysisBasis'] = 'mock_heuristics'

    try:
        opening_analysis = analyze_opening_frames_with_ai(
            analysis_report.get('ai_input', {}),
            analysis_report.get('ai_input', {}).get('frameManifest', {}),
        )
        if opening_analysis.get('_status') == 'ok':
            opening_analysis.pop('_status', None)
            opening_analysis.pop('_readableFrames', None)
            analysis_report['openingAnalysis'] = opening_analysis
            analysis_report['ai_input']['openingAnalysis'] = opening_analysis
        elif opening_analysis.get('_status') == 'invalid_response':
            ai_warnings.append('Opening AI analysis skipped: invalid model response.')
        elif opening_analysis.get('_status') == 'skipped_no_readable_frames':
            ai_warnings.append('Opening AI analysis skipped: no readable frames.')
    except Exception as exc:
        ai_warnings.append(f'Opening AI analysis failed: {exc}')

    try:
        video_intelligence = analyze_full_video_intelligence(analysis_report.get('ai_input', {}))
        if video_intelligence.get('_status') == 'ok':
            video_intelligence.pop('_status', None)
            analysis_report['videoIntelligence'] = video_intelligence
            analysis_report['ai_input']['videoIntelligence'] = video_intelligence
            if safe_confidence(video_intelligence.get('confidence')) >= 0.5:
                canonical_angle = video_intelligence.get('canonicalVideoAngle')
                if canonical_angle:
                    analysis_report['ai_input']['videoAngle'] = canonical_angle
                elif safe_confidence((analysis_report['ai_input'].get('visualAnalysis') or {}).get('confidence')) < 0.5:
                    analysis_report['ai_input']['videoAngle'] = 'generic_video'
                generation_basis = ['video_intelligence']
                if safe_confidence((analysis_report['ai_input'].get('visualAnalysis') or {}).get('confidence')) >= 0.5:
                    generation_basis.append('visual_ai')
                if audio_analysis.get('hasAudio') and (
                    transcript.get('status') in {'completed', 'empty'}
                    or audio_analysis.get('approximateLoudness') is not None
                    or audio_analysis.get('silenceRatio') is not None
                ):
                    generation_basis.append('audio_analysis')
                generation_basis.extend(['technical_fingerprint', 'user_context'])
                analysis_report['ai_input']['generationBasis'] = generation_basis
                analysis_report['ai_input']['analysisBasis'] = 'video_intelligence'
        elif video_intelligence.get('_status') == 'invalid_response':
            ai_warnings.append('Full video intelligence synthesis skipped: invalid model response.')
    except Exception as exc:
        ai_warnings.append(f'Full video intelligence synthesis failed; preserving partial analysis: {exc}')

    retention_analysis = build_retention_analysis(
        analysis_report.get('videoIntelligence'),
        analysis_report.get('openingAnalysis'),
        temporal_analysis,
    )
    analysis_report['retentionAnalysis'] = retention_analysis
    analysis_report['ai_input']['retentionAnalysis'] = retention_analysis

    print(
        '[worker][video-intelligence]',
        json.dumps({
            'job_id': job_id,
            'visualFramesSentToAI': visual_frames_sent,
            'transcriptionAttempted': transcription_attempted,
            'sceneCandidateCount': len(scene_candidates),
            'samplingStrategy': sampling_plan.get('strategy'),
        }, ensure_ascii=False),
    )

    seo_draft, ai_provider_used, ai_fallback_used, seo_warnings = generate_seo_packages(analysis_report)
    ai_warnings.extend(seo_warnings)
    analysis_report['seoDraft'] = seo_draft
    analysis_report['aiProviderUsed'] = ai_provider_used
    analysis_report['aiFallbackUsed'] = ai_fallback_used
    analysis_report['aiWarnings'] = ai_warnings

    return {
        'duration': duration,
        'resolution': f'{width}x{height}' if width and height else None,
        'fps': vstream.get('r_frame_rate'),
        'codec': vstream.get('codec_name'),
        'bitrate': meta.get('format', {}).get('bit_rate'),
        'aspect_ratio': f"{width}:{height}" if width and height else None,
        'has_audio': astream is not None,
        'frames': frames,
    }, analysis_report


def update_job(job_id, status, result=None, analysis_report=None, error=None):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    frames = result.get('frames') if result else None
    cur.execute(
        'UPDATE video_jobs SET status=%s, result=%s, frames=%s, analysis_report=%s, error=%s, updated_at=NOW() WHERE id=%s',
        (
            status,
            json.dumps(result) if result else None,
            json.dumps(frames) if frames else None,
            json.dumps(analysis_report) if analysis_report else None,
            error,
            job_id,
        )
    )
    conn.commit()
    cur.close()
    conn.close()


def load_video(storage_key: str) -> str:
    local_target = Path(tempfile.gettempdir()) / Path(storage_key).name
    if STORAGE_MODE == 'minio':
        s3 = boto3.client(
            's3',
            endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minio'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minio123')
        )
        s3.download_file(MINIO_BUCKET, storage_key, str(local_target))
    else:
        src = Path(LOCAL_STORAGE_PATH) / storage_key
        local_target.write_bytes(src.read_bytes())
    return str(local_target)


def consume_once():
    item = r.brpop('video_jobs_queue', timeout=2)
    if not item:
        return
    payload = json.loads(item[1])
    job_id = payload['id']
    try:
        update_job(job_id, 'processing')
        user_context = get_job_context(job_id)
        result, analysis_report = analyze_file(load_video(payload['storageKey']), job_id, user_context)
        update_job(job_id, 'done', result=result, analysis_report=analysis_report)
    except Exception as e:
        update_job(job_id, 'failed', error=str(e))


if __name__ == '__main__':
    while True:
        consume_once()
        time.sleep(1)
