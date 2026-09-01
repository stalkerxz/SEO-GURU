from typing import Any, Dict, List


CANONICAL_VIDEO_ANGLES = {
    'urban_drive', 'urban_drive_sunset', 'urban_drive_cinematic',
    'auto_cinematic', 'auto_detail_showcase', 'auto_review', 'auto_sale',
    'travel_destination_short', 'travel_resort_reels', 'travel_horizontal_story',
    'event_people_scene', 'event_scene', 'talking_head', 'product_showcase',
    'tutorial', 'story_reveal', 'ambient_scene', 'generic_video',
}

HOOK_TYPES = {
    'visual_reveal', 'movement', 'person', 'question', 'text', 'surprise',
    'beauty', 'information', 'product', 'story', 'ambient', 'unclear',
}

PACING_TYPES = {'very_slow', 'slow', 'medium', 'fast', 'very_fast'}


def safe_confidence(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {'high', 'medium', 'low'}:
            return {'high': 0.8, 'medium': 0.5, 'low': 0.3}[raw]
        try:
            if raw.endswith('%'):
                return max(0.0, min(1.0, float(raw[:-1]) / 100.0))
            numeric = float(raw)
            return numeric if 0.0 <= numeric <= 1.0 else numeric / 100.0 if numeric <= 100 else 0.0
        except ValueError:
            return 0.0
    return 0.0


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {'true', '1', 'yes', 'да'}
    return False


def normalize_opening_analysis(parsed: Dict[str, Any], duration_sec: float) -> Dict[str, Any]:
    hook_type = str(parsed.get('hookType', 'unclear') or 'unclear')
    if hook_type not in HOOK_TYPES:
        hook_type = 'unclear'
    return {
        'durationAnalyzedSec': round(min(3.0, max(0.0, float(duration_sec or 0.0))), 2),
        'visualSummary': str(parsed.get('visualSummary', '') or ''),
        'immediateSubject': str(parsed.get('immediateSubject', '') or ''),
        'actionStartsImmediately': _safe_bool(parsed.get('actionStartsImmediately', False)),
        'readableTextPresent': _safe_bool(parsed.get('readableTextPresent', False)),
        'hookStrength': safe_confidence(parsed.get('hookStrength')),
        'hookType': hook_type,
        'strengths': _list(parsed.get('strengths')),
        'weaknesses': _list(parsed.get('weaknesses')),
        'retentionRisk': str(parsed.get('retentionRisk', '') or ''),
        'suggestedImprovement': str(parsed.get('suggestedImprovement', '') or ''),
    }


def normalize_video_intelligence(parsed: Dict[str, Any], fallback_angle: str = '') -> Dict[str, Any]:
    story = _dict(parsed.get('story'))
    opening = _dict(parsed.get('openingHook'))
    editing = _dict(parsed.get('editing'))
    audio = _dict(parsed.get('audio'))
    retention = _dict(parsed.get('retention'))
    seo_evidence = _dict(parsed.get('seoEvidence'))
    people = _dict(parsed.get('people'))
    angle = str(parsed.get('canonicalVideoAngle', '') or '')
    if angle not in CANONICAL_VIDEO_ANGLES:
        angle = fallback_angle if fallback_angle in CANONICAL_VIDEO_ANGLES else ''
    opening_type = str(opening.get('type', 'unclear') or 'unclear')
    if opening_type not in HOOK_TYPES:
        opening_type = 'unclear'
    pacing = str(editing.get('pacing', 'medium') or 'medium')
    if pacing not in PACING_TYPES:
        pacing = 'medium'

    strongest_moments = []
    for moment in _list(parsed.get('strongestMoments')):
        if not isinstance(moment, dict):
            continue
        timestamp = moment.get('timestampSec')
        try:
            timestamp_value = max(0.0, float(timestamp))
        except (TypeError, ValueError):
            continue
        strongest_moments.append({
            'timestampSec': round(timestamp_value, 2),
            'reason': str(moment.get('reason', '') or ''),
        })

    return {
        'version': 1,
        'summary': str(parsed.get('summary', '') or ''),
        'primarySubject': str(parsed.get('primarySubject', '') or ''),
        'contentType': str(parsed.get('contentType', '') or ''),
        'contentNiche': str(parsed.get('contentNiche', '') or ''),
        'locationType': str(parsed.get('locationType', '') or ''),
        'people': {
            'present': _safe_bool(people.get('present', False)),
            'role': str(people.get('role', '') or ''),
        },
        'story': {
            'structure': str(story.get('structure', 'ambient_single_scene') or 'ambient_single_scene'),
            'beginning': str(story.get('beginning', '') or ''),
            'development': str(story.get('development', '') or ''),
            'climax': str(story.get('climax', '') or ''),
            'ending': str(story.get('ending', '') or ''),
            'payoff': str(story.get('payoff', '') or ''),
        },
        'openingHook': {
            'summary': str(opening.get('summary', '') or ''),
            'strength': safe_confidence(opening.get('strength')),
            'type': opening_type,
            'retentionRisk': str(opening.get('retentionRisk', '') or ''),
        },
        'editing': {
            'pacing': pacing,
            'estimatedSceneCount': max(0, _safe_int(editing.get('estimatedSceneCount'))),
            'cutsPerMinute': max(0.0, _safe_float(editing.get('cutsPerMinute'))),
            'averageShotDurationSec': max(0.0, _safe_float(editing.get('averageShotDurationSec'))),
            'style': _list(editing.get('style')),
            'strengths': _list(editing.get('strengths')),
            'weaknesses': _list(editing.get('weaknesses')),
        },
        'audio': {
            'hasAudio': _safe_bool(audio.get('hasAudio', False)),
            'speechPresent': _safe_bool(audio.get('speechPresent', False)),
            'speechSummary': str(audio.get('speechSummary', '') or ''),
            'audioRole': str(audio.get('audioRole', '') or ''),
            'silenceRisk': str(audio.get('silenceRisk', '') or ''),
        },
        'mood': _list(parsed.get('mood')),
        'style': _list(parsed.get('style')),
        'strongestMoments': strongest_moments,
        'retention': {
            'strengths': _list(retention.get('strengths')),
            'risks': _list(retention.get('risks')),
            'dropOffRisks': _list(retention.get('dropOffRisks')),
            'improvements': _list(retention.get('improvements')),
        },
        'visualStrengths': _list(parsed.get('visualStrengths')),
        'visualWeaknesses': _list(parsed.get('visualWeaknesses')),
        'seoEvidence': {
            'primaryTopics': _list(seo_evidence.get('primaryTopics')),
            'secondaryTopics': _list(seo_evidence.get('secondaryTopics')),
            'confirmedEntities': _list(seo_evidence.get('confirmedEntities')),
            'safeKeywords': _list(seo_evidence.get('safeKeywords')),
            'unsafeUnsupportedClaims': _list(seo_evidence.get('unsafeUnsupportedClaims')),
        },
        'recommendedContentAngle': str(parsed.get('recommendedContentAngle', '') or ''),
        'canonicalVideoAngle': angle,
        'confidence': safe_confidence(parsed.get('confidence')),
    }


def build_retention_analysis(
    video_intelligence: Dict[str, Any] | None,
    opening_analysis: Dict[str, Any] | None,
    temporal_analysis: Dict[str, Any] | None,
) -> Dict[str, Any]:
    intelligence = video_intelligence or {}
    opening = opening_analysis or {}
    temporal = temporal_analysis or {}
    retention = _dict(intelligence.get('retention'))
    opening_hook = _dict(intelligence.get('openingHook'))
    return {
        'estimatedHookStrength': safe_confidence(
            opening_hook.get('strength', opening.get('hookStrength'))
        ),
        'visualChangeRate': str(temporal.get('pacing', 'unknown') or 'unknown'),
        'strengths': _list(retention.get('strengths')) or _list(opening.get('strengths')),
        'risks': _list(retention.get('risks')) or _list(opening.get('weaknesses')),
        'dropOffRisks': _list(retention.get('dropOffRisks')),
        'recommendedEdits': _list(retention.get('improvements')) or (
            [opening.get('suggestedImprovement')] if opening.get('suggestedImprovement') else []
        ),
        'disclaimer': 'Экспертная оценка по структуре ролика, не фактическая аналитика удержания.',
    }
