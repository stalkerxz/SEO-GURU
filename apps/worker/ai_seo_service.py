import json
import os
import re
import base64
from typing import Any, Dict, List, Tuple

import boto3
from openai import OpenAI

from seo_mock_generator import generate_mock_seo_package
from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt

PLATFORMS = ['youtubeVideo', 'youtubeShorts', 'instagramReels', 'tiktok']

STRUCTURAL_FIELDS = {
    'platform', 'language', 'userGoal', 'niche', 'resolution', 'aspectRatio',
    'orientation', 'videoDurationSec', 'score', 'videoAngle', 'generationBasis',
    'analysisBasis', 'seoCompletionMode',
}

REQUIRED_SEMANTIC_FIELDS = {
    'youtubeShorts': [
        'hookText', 'bestTitle', 'titleOptions', 'description', 'hashtags',
        'coverText', 'pinnedComment', 'improvementTips',
    ],
    'youtubeVideo': [
        'bestTitle', 'titleOptions', 'description', 'tags', 'thumbnailText',
        'pinnedComment', 'improvementTips',
    ],
    'instagramReels': [
        'firstLineHook', 'caption', 'hashtags', 'coverText', 'storyAnnouncement',
        'cta', 'altText', 'improvementTips',
    ],
    'tiktok': [
        'hookText', 'caption', 'hashtags', 'coverText', 'trendAngle', 'cta',
        'improvementTips',
    ],
}

# Each group represents one specific claim. Any alias in generated copy is allowed
# only when another alias is present in authoritative visual evidence.
SPECIFIC_CLAIM_GROUPS = {
    'drift': ['drift', 'drifting', 'дрифт', 'дрифта', 'дрифтом', 'дрифтинг'],
    'smoke': ['smoke', 'tire smoke', 'дым', 'дыма', 'дымом'],
    'burnout': ['burnout', 'burn-out', 'бернаут', 'прожиг резины'],
    'phonk': ['phonk', 'фонк'],
    'race': ['race', 'racing', 'гонка', 'гонки', 'гонку', 'гоночный'],
    'speed': ['speed', 'speeding', 'скорость', 'скорости', 'превышение скорости'],
    'wedding': ['wedding', 'свадьба', 'свадебный'],
    'concert': ['concert', 'концерт'],
    'beach': ['beach', 'пляж'],
    'mountains': ['mountain', 'mountains', 'гора', 'горы', 'горный'],
    'restaurant': ['restaurant', 'ресторан'],
    'product': ['product showcase', 'product review', 'обзор продукта', 'демонстрация товара'],
}


def safe_confidence(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {'high', 'medium', 'low'}:
            return {'high': 0.8, 'medium': 0.5, 'low': 0.3}[raw]
        try:
            if raw.endswith('%'):
                return max(0.0, min(1.0, float(raw[:-1].strip()) / 100.0))
            numeric = float(raw)
            if 0 <= numeric <= 1:
                return numeric
            if 1 < numeric <= 100:
                return numeric / 100.0
        except ValueError:
            return 0.0
    return 0.0


def _env_timeout_seconds() -> float:
    raw = os.getenv('AI_TIMEOUT_SECONDS', '60')
    try:
        value = float(raw)
        return value if value > 0 else 60.0
    except ValueError:
        return 60.0


def extract_json_from_text(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```json\s*|^```\s*|\s*```$', '', cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _as_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(values: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def _sentence(value: str) -> str:
    cleaned = re.sub(r'\s+', ' ', str(value or '')).strip(' .,:;\n\t')
    if not cleaned:
        return ''
    return cleaned[0].upper() + cleaned[1:]


def _short_cover(value: str, max_words: int = 6) -> str:
    words = _sentence(value).split()
    return ' '.join(words[:max_words]).upper()


def _evidence_hashtags(platform: str, visual: Dict[str, Any], language: str) -> List[str]:
    source = ' '.join([
        str(visual.get('detectedScene', '')),
        str(visual.get('summary', '')),
        ' '.join(_as_text_list(visual.get('detectedObjects'))),
        str(visual.get('suggestedNiche', '')),
    ])
    stop_words = {
        'the', 'and', 'with', 'from', 'this', 'that', 'video',
        'это', 'как', 'для', 'или', 'над', 'под', 'при', 'который', 'которая',
        'движущимися', 'пейзаж',
    }
    tokens = [
        token for token in re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', source)
        if len(token) >= 3 and token.casefold() not in stop_words
    ]
    platform_tag = {
        'youtubeShorts': 'Shorts',
        'instagramReels': 'Reels',
        'tiktok': 'TikTok',
    }.get(platform)
    tags = [f'#{platform_tag}'] if platform_tag else []
    tags.extend(f'#{token}' for token in _dedupe(tokens)[:6])
    if not tags:
        tags = ['#Video' if language.startswith('en') else '#Видео']
    return tags[:7]


def build_visual_semantic_fallback(
    platform: str,
    ai_input: Dict[str, Any],
    visual_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Build missing publication copy exclusively from authoritative visual evidence."""
    language = str(ai_input.get('language', 'ru') or 'ru').lower()
    english = language.startswith('en')
    summary = _sentence(visual_analysis.get('summary') or visual_analysis.get('detectedScene'))
    scene = _sentence(visual_analysis.get('detectedScene') or summary)
    hooks = _dedupe(_as_text_list(visual_analysis.get('seoHooks')))
    cover_ideas = _dedupe(_as_text_list(visual_analysis.get('coverTextIdeas')))
    styles = _dedupe(_as_text_list(visual_analysis.get('style')))
    moods = _dedupe(_as_text_list(visual_analysis.get('mood')))
    weaknesses = _dedupe(_as_text_list(visual_analysis.get('visualWeaknesses')))
    suggested_angle = _sentence(visual_analysis.get('suggestedVideoAngle'))

    if not summary:
        summary = 'The scene shown in the video' if english else 'Сцена, показанная в видео'
    if not scene:
        scene = summary

    hook = _sentence(hooks[0] if hooks else summary)
    title_candidates = _dedupe([
        summary,
        scene,
        *[_sentence(item) for item in hooks],
        _sentence(f'{scene}: {styles[0]}') if styles else '',
        _sentence(f'{scene}: {moods[0]}') if moods else '',
    ])
    if len(title_candidates) == 1:
        suffix = 'A closer look' if english else 'Взгляд в деталях'
        title_candidates.append(f'{title_candidates[0]} — {suffix}')
    best_title = title_candidates[0]
    cover_text = _short_cover(cover_ideas[0] if cover_ideas else scene)
    description_parts = [summary]
    if styles:
        description_parts.append(('Visual style: ' if english else 'Визуальный стиль: ') + ', '.join(styles[:2]))
    if moods:
        description_parts.append(('Mood: ' if english else 'Настроение: ') + ', '.join(moods[:2]))
    description = '. '.join(part.rstrip('.') for part in description_parts if part) + '.'
    hashtags = _evidence_hashtags(platform, visual_analysis, language)
    evidence_tags = [tag.lstrip('#') for tag in hashtags if tag.lstrip('#').casefold() not in {'shorts', 'reels', 'tiktok'}]
    if not evidence_tags:
        evidence_tags = ['video' if english else 'видео']
    improvement_tips = weaknesses or [
        'Keep the strongest visual in the opening seconds.' if english
        else 'Поставьте самый сильный визуальный кадр в первые секунды.'
    ]
    pinned_comment = (
        'What detail in this scene caught your attention?' if english
        else 'Какая деталь этой сцены привлекла ваше внимание?'
    )
    cta = 'Save the video if this mood resonates with you.' if english else 'Сохраните ролик, если вам близка эта атмосфера.'

    common = {
        'bestTitle': best_title,
        'titleOptions': title_candidates[:5],
        'description': description,
        'caption': description,
        'hookText': hook,
        'firstLineHook': hook,
        'coverText': cover_text,
        'thumbnailText': cover_text,
        'pinnedComment': pinned_comment,
        'hashtags': hashtags,
        'tags': evidence_tags[:10],
        'trendAngle': suggested_angle or _sentence(styles[0] if styles else scene),
        'storyAnnouncement': (
            f'New video: {summary}.' if english else f'Новый ролик: {summary}.'
        ),
        'cta': cta,
        'altText': summary,
        'improvementTips': improvement_tips,
    }
    return {field: common[field] for field in REQUIRED_SEMANTIC_FIELDS[platform] if field in common} | {
        'pinnedComment': common['pinnedComment']
    }


def _visual_evidence_blob(visual: Dict[str, Any]) -> str:
    values: List[str] = []
    for field in [
        'summary', 'detectedObjects', 'detectedScene', 'style', 'seoHooks',
        'suggestedVideoAngle',
    ]:
        value = visual.get(field)
        values.extend(_as_text_list(value))
    return ' '.join(values).casefold()


def _contains_alias(text: str, aliases: List[str]) -> bool:
    normalized = text.casefold()
    return any(re.search(rf'(?<!\w){re.escape(alias.casefold())}(?!\w)', normalized) for alias in aliases)


def _unsupported_claims(value: Any, evidence: str) -> List[str]:
    if isinstance(value, str):
        value_text = value
    elif isinstance(value, list):
        value_text = ' '.join(str(item) for item in value if isinstance(item, str))
    else:
        return []
    return [
        claim for claim, aliases in SPECIFIC_CLAIM_GROUPS.items()
        if _contains_alias(value_text, aliases) and not _contains_alias(evidence, aliases)
    ]


def _sanitize_visual_fallback(
    fallback: Dict[str, Any],
    visual: Dict[str, Any],
    language: str,
) -> Tuple[Dict[str, Any], List[str]]:
    evidence = _visual_evidence_blob(visual)
    english = language.lower().startswith('en')
    neutral = _sentence(visual.get('summary') or visual.get('detectedScene'))
    neutral_cover = _short_cover(visual.get('detectedScene') or neutral)
    sanitized = dict(fallback)
    warnings: List[str] = []

    for field, value in fallback.items():
        unsupported = _unsupported_claims(value, evidence)
        if not unsupported:
            continue
        for claim in unsupported:
            warning = f'Unsupported SEO claim sanitized: {claim}'
            if warning not in warnings:
                warnings.append(warning)
        if field in {'coverText', 'thumbnailText'}:
            sanitized[field] = neutral_cover
        elif field == 'titleOptions':
            sanitized[field] = [neutral] if neutral else []
        elif field == 'improvementTips':
            sanitized[field] = [
                'Keep the strongest visual in the opening seconds.' if english
                else 'Поставьте самый сильный визуальный кадр в первые секунды.'
            ]
        elif isinstance(value, list):
            sanitized[field] = [neutral] if neutral else []
        else:
            sanitized[field] = neutral
    return sanitized, warnings


def _authoritative_generation_basis(ai_input: Dict[str, Any]) -> List[str]:
    basis = ['visual_ai']
    if ai_input.get('technicalSummary') or ai_input.get('videoFingerprint'):
        basis.append('technical_fingerprint')
    basis.append('user_context')
    return basis


def _structural_values(platform: str, ai_input: Dict[str, Any]) -> Dict[str, Any]:
    technical = ai_input.get('technicalSummary', {}) or {}
    fingerprint = ai_input.get('videoFingerprint', {}) or {}
    platform_fit = (ai_input.get('platformFit', {}) or {}).get(platform)
    score = platform_fit.get('score') if isinstance(platform_fit, dict) else platform_fit
    return {
        'platform': platform,
        'language': ai_input.get('language', ''),
        'userGoal': ai_input.get('userGoal', ''),
        'niche': ai_input.get('niche', ''),
        'resolution': technical.get('resolution'),
        'aspectRatio': technical.get('aspectRatio'),
        'orientation': fingerprint.get('orientation'),
        'videoDurationSec': technical.get('durationSec'),
        'score': score,
        'videoAngle': ai_input.get('videoAngle', ''),
        'generationBasis': _authoritative_generation_basis(ai_input),
        'analysisBasis': 'visual_ai',
    }


def _complete_visual_ai_package(
    platform: str,
    ai_input: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    visual = ai_input.get('visualAnalysis', {}) or {}
    fallback = build_visual_semantic_fallback(platform, ai_input, visual)
    fallback, fallback_warnings = _sanitize_visual_fallback(
        fallback,
        visual,
        str(ai_input.get('language', 'ru') or 'ru'),
    )
    evidence = _visual_evidence_blob(visual)
    package: Dict[str, Any] = {}
    warnings: List[str] = list(fallback_warnings)
    completed_locally = bool(fallback_warnings)

    for key, value in candidate.items():
        if key in STRUCTURAL_FIELDS or not _is_present(value):
            continue
        unsupported = _unsupported_claims(value, evidence)
        if unsupported:
            completed_locally = True
            for claim in unsupported:
                warning = f'Unsupported SEO claim sanitized: {claim}'
                if warning not in warnings:
                    warnings.append(warning)
            if _is_present(fallback.get(key)):
                package[key] = fallback[key]
            continue
        package[key] = value

    for field in REQUIRED_SEMANTIC_FIELDS[platform]:
        if not _is_present(package.get(field)):
            package[field] = fallback.get(field, [] if field.endswith(('Options', 'Tips')) else '')
            completed_locally = True

    # Keep useful optional fields evidence-based as well, without importing any mock copy.
    for field in ['pinnedComment']:
        if not _is_present(package.get(field)) and _is_present(fallback.get(field)):
            package[field] = fallback[field]
            completed_locally = True

    package.update({key: value for key, value in _structural_values(platform, ai_input).items() if _is_present(value)})
    package['seoCompletionMode'] = 'ai_visual_completion' if completed_locally else 'ai_complete'
    return package, warnings


def _platform_prompt_input(ai_input: Dict[str, Any]) -> Dict[str, Any]:
    """Remove legacy semantic hints from the high-confidence visual-AI prompt path."""
    visual = ai_input.get('visualAnalysis', {}) or {}
    if safe_confidence(visual.get('confidence')) < 0.5:
        return ai_input

    prompt_input = dict(ai_input)
    prompt_input.pop('recommendations', None)
    prompt_input.pop('detectedIssues', None)
    fingerprint = prompt_input.get('videoFingerprint')
    if isinstance(fingerprint, dict):
        prompt_input['videoFingerprint'] = {
            key: value for key, value in fingerprint.items()
            if key not in {'filenameTokens', 'detectedModel', 'contentHints'}
        }
    weak_metadata = {
        'originalFilename': prompt_input.pop('originalFilename', ''),
        'extractedFilenameHints': prompt_input.pop('extractedFilenameHints', {}),
        'contentHints': prompt_input.pop('contentHints', []),
    }
    prompt_input['weakMetadata'] = weak_metadata
    return prompt_input


def _has_authoritative_visual(ai_input: Dict[str, Any]) -> bool:
    visual = ai_input.get('visualAnalysis', {}) if isinstance(ai_input, dict) else {}
    return bool(visual) and safe_confidence((visual or {}).get('confidence')) >= 0.5


def _merge_with_mock(platform: str, analysis_report: Dict[str, Any], candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    mock = generate_mock_seo_package(analysis_report, platform)
    if not isinstance(candidate, dict):
        return mock
    merged = dict(mock)
    for key, value in candidate.items():
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, list) and len(value) == 0):
            continue
        merged[key] = value
    canonical_angle = (analysis_report.get('ai_input', {}) or {}).get('videoAngle')
    if canonical_angle:
        merged['videoAngle'] = canonical_angle
    return merged


def _openai_platform_json(platform: str, ai_input: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=timeout_seconds)
    model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')

    prompt_input = _platform_prompt_input(ai_input)
    response = client.responses.create(
        model=model,
        input=[
            {'role': 'system', 'content': 'Return only valid JSON. Follow the user constraints strictly.'},
            {'role': 'user', 'content': f"{build_ai_video_analysis_prompt(prompt_input)}\n\n{build_platform_seo_prompt(platform, prompt_input)}"},
        ],
    )
    return extract_json_from_text(response.output_text)


def generate_openai_seo_packages(analysis_report: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], List[str], bool]:
    ai_input = analysis_report.get('ai_input', {})
    timeout_seconds = _env_timeout_seconds()
    packages: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    fallback_used = False

    for platform in PLATFORMS:
        try:
            candidate = _openai_platform_json(platform, ai_input, timeout_seconds)
            visual = ai_input.get('visualAnalysis', {}) if isinstance(ai_input, dict) else {}
            if isinstance(candidate, dict) and safe_confidence((visual or {}).get('confidence')) >= 0.5:
                package, package_warnings = _complete_visual_ai_package(platform, ai_input, candidate)
                packages[platform] = package
                for warning in package_warnings:
                    if warning not in warnings:
                        warnings.append(warning)
            else:
                packages[platform] = _merge_with_mock(platform, analysis_report, candidate)
        except Exception:
            fallback_used = True
            if _has_authoritative_visual(ai_input):
                warning = f'AI platform generation failed for {platform}; completed from visual evidence.'
                package, package_warnings = _complete_visual_ai_package(platform, ai_input, {})
                packages[platform] = package
                for package_warning in package_warnings:
                    if package_warning not in warnings:
                        warnings.append(package_warning)
            else:
                warning = f'AI response parsing failed for {platform}, used mock fallback.'
                packages[platform] = generate_mock_seo_package(analysis_report, platform)
            print(f'[AI WARNING] {warning}')
            warnings.append(warning)

    return packages, warnings, fallback_used


def generate_seo_packages(analysis_report: Dict[str, Any]) -> Tuple[Dict[str, Any], str, bool, List[str]]:
    provider = os.getenv('AI_PROVIDER', 'mock').lower().strip() or 'mock'
    warnings: List[str] = []

    if provider != 'openai':
        seo = {platform: generate_mock_seo_package(analysis_report, platform) for platform in PLATFORMS}
        return seo, 'mock', False, warnings

    if not os.getenv('OPENAI_API_KEY', '').strip():
        warning = 'AI_PROVIDER=openai, but OPENAI_API_KEY is empty. Fallback to mock provider.'
        print(f'[AI WARNING] {warning}')
        warnings.append(warning)
        seo = {platform: generate_mock_seo_package(analysis_report, platform) for platform in PLATFORMS}
        return seo, 'mock', True, warnings

    try:
        seo, openai_warnings, fallback_used = generate_openai_seo_packages(analysis_report)
        warnings.extend(openai_warnings)
        return seo, 'openai', fallback_used, warnings
    except Exception:
        ai_input = analysis_report.get('ai_input', {})
        if _has_authoritative_visual(ai_input):
            warning = 'AI provider failed globally; completed all platforms from visual evidence.'
            print(f'[AI WARNING] {warning}')
            warnings.append(warning)
            seo = {}
            for platform in PLATFORMS:
                package, package_warnings = _complete_visual_ai_package(platform, ai_input, {})
                seo[platform] = package
                for package_warning in package_warnings:
                    if package_warning not in warnings:
                        warnings.append(package_warning)
            return seo, 'openai', True, warnings
        warning = 'AI provider failed globally, used mock fallback.'
        print(f'[AI WARNING] {warning}')
        warnings.append(warning)
        seo = {platform: generate_mock_seo_package(analysis_report, platform) for platform in PLATFORMS}
        return seo, 'mock', True, warnings
def analyze_video_frames_with_ai(ai_input: Dict[str, Any], frame_manifest: Dict[str, Any]) -> Dict[str, Any]:
    provider = os.getenv('AI_PROVIDER', 'mock').lower().strip() or 'mock'
    if provider != 'openai' or not os.getenv('OPENAI_API_KEY', '').strip():
        return {}

    frames = (frame_manifest or {}).get('frames', [])
    if not isinstance(frames, list) or not frames:
        return {}

    selected = frames[: min(6, len(frames))]
    content: List[Dict[str, Any]] = [{
        'type': 'input_text',
        'text': (
            'Analyze these frames as representative frames from one video. '
            'Do not invent objects not visible in the frames. If uncertain, say uncertain. '
            'Determine whether this is travel, auto, event, real estate, beauty, food, education, product, or generic. '
            'Identify what should drive SEO. Suggest platform-specific content angles. Return only valid JSON. '
            'Ответ JSON. Тексты summary/hooks/coverTextIdeas на языке userContext.language. '
            'Не использовать filename как основной источник. Filename можно учитывать только как weak hint. '
            'JSON schema: {"summary":"","detectedObjects":[],"detectedScene":"","detectedLocationType":"",'
            '"peoplePresent":false,"vehiclePresent":false,"travelContent":false,"autoContent":false,'
            '"eventContent":false,"productContent":false,"style":[],"mood":[],"visualStrengths":[],'
            '"visualWeaknesses":[],"bestFrames":[{"frameIndex":0,"reason":""}],"suggestedNiche":"",'
            '"suggestedVideoAngle":"","seoHooks":[],"coverTextIdeas":[],"confidence":0.0}'
        ),
    }]

    storage_mode = os.getenv('STORAGE_MODE', 'local')
    s3_client = None
    if storage_mode == 'minio':
        s3_client = boto3.client(
            's3',
            endpoint_url=f"http{'s' if str(os.getenv('MINIO_USE_SSL', 'false')).lower() == 'true' else ''}://{os.getenv('MINIO_ENDPOINT', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minio'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minio123'),
        )

    readable_count = 0
    for frame in selected:
        storage_key = frame.get('storageKey')
        if not storage_key:
            continue
        frame_bytes = b''
        try:
            if storage_mode == 'minio' and s3_client is not None:
                obj = s3_client.get_object(Bucket=os.getenv('MINIO_BUCKET', 'videos'), Key=storage_key)
                frame_bytes = obj['Body'].read()
            else:
                file_path = os.path.join(os.getenv('LOCAL_STORAGE_PATH', '/app/storage'), storage_key)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as fp:
                        frame_bytes = fp.read()
            if not frame_bytes:
                print(f'[AI WARNING] Unable to read frame bytes: {storage_key}')
                continue
        except Exception as exc:
            print(f'[AI WARNING] Frame read failed for {storage_key}: {exc}')
            continue
        encoded = base64.b64encode(frame_bytes).decode('utf-8')
        content.append({'type': 'input_image', 'image_url': f'data:image/jpeg;base64,{encoded}'})
        readable_count += 1

    if len(content) <= 1:
        return {'_status': 'skipped_no_readable_frames'}

    timeout_seconds = _env_timeout_seconds()
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=timeout_seconds)
    model = os.getenv('OPENAI_VISION_MODEL', os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    response = client.responses.create(
        model=model,
        input=[
            {'role': 'system', 'content': 'Return only valid JSON.'},
            {'role': 'user', 'content': content},
        ],
    )
    try:
        parsed = extract_json_from_text(response.output_text)
    except Exception as exc:
        print(f'[AI WARNING] Vision JSON parsing failed: {exc}')
        return {'_status': 'invalid_response'}

    if not isinstance(parsed, dict):
        return {'_status': 'invalid_response'}

    if not (parsed.get('summary') or parsed.get('detectedObjects') or parsed.get('confidence') is not None):
        return {'_status': 'invalid_response'}

    normalized = {
        'summary': parsed.get('summary', ''),
        'detectedObjects': parsed.get('detectedObjects', []),
        'detectedScene': parsed.get('detectedScene', ''),
        'detectedLocationType': parsed.get('detectedLocationType', ''),
        'peoplePresent': bool(parsed.get('peoplePresent', False)),
        'vehiclePresent': bool(parsed.get('vehiclePresent', False)),
        'travelContent': bool(parsed.get('travelContent', False)),
        'autoContent': bool(parsed.get('autoContent', False)),
        'eventContent': bool(parsed.get('eventContent', False)),
        'productContent': bool(parsed.get('productContent', False)),
        'style': parsed.get('style', []),
        'mood': parsed.get('mood', []),
        'visualStrengths': parsed.get('visualStrengths', []),
        'visualWeaknesses': parsed.get('visualWeaknesses', []),
        'bestFrames': parsed.get('bestFrames', []),
        'suggestedNiche': parsed.get('suggestedNiche', ''),
        'suggestedVideoAngle': parsed.get('suggestedVideoAngle', ''),
        'seoHooks': parsed.get('seoHooks', []),
        'coverTextIdeas': parsed.get('coverTextIdeas', []),
        'confidence': safe_confidence(parsed.get('confidence')),
        '_status': 'ok',
        '_readableFrames': readable_count,
    }
    return normalized
