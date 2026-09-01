import os
import re
import statistics
import subprocess
from typing import Any, Dict, List


DEFAULT_SCENE_THRESHOLD = 0.35


def scene_threshold() -> float:
    raw = os.getenv('VIDEO_SCENE_THRESHOLD', str(DEFAULT_SCENE_THRESHOLD))
    try:
        return max(0.05, min(0.95, float(raw)))
    except (TypeError, ValueError):
        return DEFAULT_SCENE_THRESHOLD


def detect_scene_changes(file_path: str, threshold: float | None = None) -> List[float]:
    configured_threshold = scene_threshold() if threshold is None else max(0.05, min(0.95, float(threshold)))
    command = [
        'ffmpeg', '-hide_banner', '-i', file_path,
        '-filter:v', f"select='gt(scene,{configured_threshold})',showinfo",
        '-an', '-f', 'null', '-',
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f'ffmpeg scene detection exited with code {completed.returncode}')
    timestamps = [float(value) for value in re.findall(r'pts_time:([0-9]+(?:\.[0-9]+)?)', completed.stderr)]
    return sorted({round(timestamp, 3) for timestamp in timestamps if timestamp >= 0.0})


def pacing_from_cuts_per_minute(cuts_per_minute: float) -> str:
    if cuts_per_minute < 2:
        return 'very_slow'
    if cuts_per_minute < 6:
        return 'slow'
    if cuts_per_minute < 12:
        return 'medium'
    if cuts_per_minute < 24:
        return 'fast'
    return 'very_fast'


def _valid_scene_timestamps(values: List[float] | None, duration_sec: float) -> List[float]:
    valid = set()
    for value in values or []:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            continue
        if 0.0 < timestamp < duration_sec:
            valid.add(round(timestamp, 3))
    return sorted(valid)


def build_temporal_analysis(duration_sec: float, scene_timestamps: List[float] | None) -> Dict[str, Any]:
    duration = max(0.0, float(duration_sec or 0.0))
    changes = _valid_scene_timestamps(scene_timestamps, duration)
    boundaries = [0.0, *changes, duration] if duration > 0 else [0.0]
    shot_durations = [
        max(0.0, boundaries[index + 1] - boundaries[index])
        for index in range(len(boundaries) - 1)
    ]
    cuts_per_minute = (len(changes) / duration * 60.0) if duration > 0 else 0.0
    average_shot = (sum(shot_durations) / len(shot_durations)) if shot_durations else 0.0
    median_shot = statistics.median(shot_durations) if shot_durations else 0.0
    return {
        'sceneChangeTimestampsSec': changes,
        'estimatedSceneCount': len(changes) + 1 if duration > 0 else 0,
        'cutsPerMinute': round(cuts_per_minute, 2),
        'averageShotDurationSec': round(average_shot, 2),
        'medianShotDurationSec': round(median_shot, 2),
        'pacing': pacing_from_cuts_per_minute(cuts_per_minute),
    }
