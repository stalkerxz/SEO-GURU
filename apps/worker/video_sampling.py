import os
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_MAX_FRAMES = 24
MIN_FRAME_GAP_SEC = 0.2


def _configured_max_frames() -> int:
    raw = os.getenv('VIDEO_AI_MAX_FRAMES', str(DEFAULT_MAX_FRAMES))
    try:
        return max(6, min(DEFAULT_MAX_FRAMES, int(raw)))
    except (TypeError, ValueError):
        return DEFAULT_MAX_FRAMES


def target_frame_count(duration_sec: float, max_frames: int | None = None) -> int:
    duration = max(0.0, float(duration_sec or 0.0))
    if duration <= 15:
        target = 8
    elif duration <= 30:
        target = 10
    elif duration <= 60:
        target = 12
    elif duration <= 180:
        target = 16
    elif duration <= 600:
        target = 20
    else:
        target = 24
    hard_max = _configured_max_frames() if max_frames is None else max(6, min(DEFAULT_MAX_FRAMES, int(max_frames)))
    return min(target, hard_max)


def _spread(values: List[float], limit: int) -> List[float]:
    if limit <= 0 or not values:
        return []
    if len(values) <= limit:
        return values
    if limit == 1:
        return [values[len(values) // 2]]
    indexes = [round(index * (len(values) - 1) / (limit - 1)) for index in range(limit)]
    return [values[index] for index in indexes]


def _uniform_anchors(duration_sec: float, count: int) -> List[float]:
    if count <= 0:
        return []
    duration = max(0.0, duration_sec)
    if duration <= 0:
        return [0.0]
    return [duration * index / (count + 1) for index in range(1, count + 1)]


def _is_duplicate(timestamp: float, selected: Iterable[Tuple[float, str]]) -> bool:
    return any(abs(timestamp - existing) < MIN_FRAME_GAP_SEC for existing, _ in selected)


def _valid_timestamps(values: List[float] | None, last_extractable: float) -> List[float]:
    valid = set()
    for value in values or []:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            continue
        if 0.0 < timestamp < last_extractable:
            valid.add(round(timestamp, 3))
    return sorted(valid)


def build_sampling_plan(
    duration_sec: float,
    scene_candidates: List[float] | None = None,
    *,
    max_frames: int | None = None,
    scene_detection_failed: bool = False,
) -> Dict[str, Any]:
    duration = max(0.0, float(duration_sec or 0.0))
    target = target_frame_count(duration, max_frames=max_frames)
    last_extractable = max(0.0, duration - 0.05)
    selected: List[Tuple[float, str]] = []

    def add(timestamp: float, source: str) -> bool:
        clamped = max(0.0, min(last_extractable, float(timestamp)))
        if _is_duplicate(clamped, selected):
            return False
        if len(selected) >= target:
            return False
        selected.append((clamped, source))
        return True

    for timestamp in [0.0, 0.5, 1.0, 2.0, 3.0]:
        if timestamp <= last_extractable:
            add(timestamp, 'opening')

    if duration > 0:
        add(last_extractable, 'ending')

    valid_scenes = _valid_timestamps(scene_candidates, last_extractable)
    remaining_after_mandatory = max(0, target - len(selected))
    scene_limit = min(len(valid_scenes), max(1, round(target * 0.45)), remaining_after_mandatory)
    for timestamp in _spread(valid_scenes, scene_limit):
        add(timestamp, 'scene')

    # Generate extra anchors so deduplication around opening/scene timestamps still
    # leaves enough unique representative frames.
    for timestamp in _uniform_anchors(duration, target * 4):
        if len(selected) >= target:
            break
        add(timestamp, 'uniform')

    selected.sort(key=lambda item: item[0])
    counts = {
        source: sum(1 for _, selected_source in selected if selected_source == source)
        for source in ['opening', 'scene', 'uniform', 'ending']
    }
    if scene_detection_failed:
        strategy = 'adaptive_uniform_fallback'
    elif counts['scene']:
        strategy = 'adaptive_scene_aware'
    else:
        strategy = 'adaptive_uniform'

    return {
        'strategy': strategy,
        'durationSec': round(duration, 3),
        'targetFrameCount': target,
        'openingFrameCount': counts['opening'],
        'sceneFrameCount': counts['scene'],
        'uniformFrameCount': counts['uniform'],
        'endingFrameCount': counts['ending'],
        'selectedTimestampsSec': [round(timestamp, 3) for timestamp, _ in selected],
    }
