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


def _merge_with_mock(platform: str, analysis_report: Dict[str, Any], candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    mock = generate_mock_seo_package(analysis_report, platform)
    if not isinstance(candidate, dict):
        return mock
    merged = dict(mock)
    for key, value in candidate.items():
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, list) and len(value) == 0):
            continue
        merged[key] = value
    return merged


def _openai_platform_json(platform: str, ai_input: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=timeout_seconds)
    model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')

    response = client.responses.create(
        model=model,
        input=[
            {'role': 'system', 'content': 'Return only valid JSON. Follow the user constraints strictly.'},
            {'role': 'user', 'content': f"{build_ai_video_analysis_prompt(ai_input)}\n\n{build_platform_seo_prompt(platform, ai_input)}"},
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
            packages[platform] = _merge_with_mock(platform, analysis_report, candidate)
        except Exception:
            fallback_used = True
            warning = f'AI response parsing failed for {platform}, used mock fallback.'
            print(f'[AI WARNING] {warning}')
            warnings.append(warning)
            packages[platform] = generate_mock_seo_package(analysis_report, platform)

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
