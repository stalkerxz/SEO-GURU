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

from ai_seo_service import generate_seo_packages
from seo_mock_generator import build_video_angle

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://video:video@localhost:5432/video_seo')
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', '/app/storage')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'videos')

r = redis.from_url(REDIS_URL)


def ffprobe_json(file_path: str):
    cmd = ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', file_path]
    return json.loads(subprocess.check_output(cmd).decode('utf-8'))


def extract_frames(file_path: str, out_dir: str, duration: float):
    fps = '1/5' if duration <= 60 else '1/10' if duration <= 300 else '1/20'
    pattern = str(Path(out_dir) / 'frame_%04d.jpg')
    subprocess.check_call(['ffmpeg', '-i', file_path, '-vf', f'fps={fps}', '-q:v', '2', pattern, '-y'])
    return sorted([Path(out_dir) / f for f in os.listdir(out_dir) if f.endswith('.jpg')])


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
    source_chunks = [
        user_context.get('originalFilename', ''),
        ' '.join(user_context.get('keywords', []) if isinstance(user_context.get('keywords', []), list) else []),
        ' '.join((user_context.get('extractedFilenameHints', {}) or {}).get('tokens', [])),
        json.dumps(technical_summary, ensure_ascii=False),
    ]
    text = ' '.join(source_chunks).lower()
    hint_rules = {
        'auto_model': ['bmw', 'x3', 'x5'],
        'drift': ['drift', 'дрифт'],
        'phonk_music': ['phonk', 'фонк'],
        'cinematic_style': ['cinematic', 'синематик'],
        'night_scene': ['night', 'ноч', 'lights'],
        'city_scene': ['city', 'город', 'urban'],
        'interior': ['interior', 'салон'],
        'review': ['review', 'обзор'],
        'sale_video': ['sale', 'продажа', 'for sale'],
    }
    return [hint for hint, terms in hint_rules.items() if any(term in text for term in terms)]




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

    with tempfile.TemporaryDirectory() as d:
        frame_files = extract_frames(file_path, d, duration)
        frames = []
        frame_count = len(frame_files)
        if STORAGE_MODE == 'minio':
            s3 = boto3.client(
                's3',
                endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
                aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minio'),
                aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minio123')
            )
            for i, f in enumerate(frame_files, start=1):
                approx_time_sec = round((duration / frame_count) * (i - 1), 2) if frame_count else 0
                frames.append(upload_frame(s3, f, job_id, i, approx_time_sec))
        else:
            for i, f in enumerate(frame_files, start=1):
                approx_time_sec = round((duration / frame_count) * (i - 1), 2) if frame_count else 0
                frames.append(persist_local_frame(f, job_id, i, approx_time_sec))

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

    seo_draft, ai_provider_used, ai_fallback_used, ai_warnings = generate_seo_packages(analysis_report)
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
