import re
import subprocess
from pathlib import Path
from typing import Any, Dict


def no_audio_analysis(duration_sec: float = 0.0) -> Dict[str, Any]:
    return {
        'hasAudio': False,
        'durationSec': round(max(0.0, float(duration_sec or 0.0)), 3),
        'codec': None,
        'channels': None,
        'sampleRate': None,
        'silenceRatio': 1.0,
        'approximateLoudness': None,
        'speechPresent': False,
        'transcriptionStatus': 'no_audio',
    }


def _silence_duration(stderr: str, duration_sec: float) -> float:
    total = 0.0
    current_start = None
    for line in stderr.splitlines():
        start_match = re.search(r'silence_start:\s*([0-9]+(?:\.[0-9]+)?)', line)
        if start_match:
            current_start = float(start_match.group(1))
        end_match = re.search(r'silence_end:\s*([0-9]+(?:\.[0-9]+)?)', line)
        if end_match and current_start is not None:
            total += max(0.0, float(end_match.group(1)) - current_start)
            current_start = None
    if current_start is not None and duration_sec > current_start:
        total += duration_sec - current_start
    return min(max(0.0, total), max(0.0, duration_sec))


def analyze_audio_technical(
    file_path: str,
    audio_stream: Dict[str, Any] | None,
    duration_sec: float,
) -> Dict[str, Any]:
    duration = max(0.0, float(duration_sec or 0.0))
    if not audio_stream:
        return no_audio_analysis(duration)

    command = [
        'ffmpeg', '-hide_banner', '-i', file_path, '-vn',
        '-af', 'silencedetect=noise=-35dB:d=0.5,volumedetect',
        '-f', 'null', '-',
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f'ffmpeg audio analysis exited with code {completed.returncode}')

    mean_volume_match = re.search(r'mean_volume:\s*(-?[0-9]+(?:\.[0-9]+)?)\s*dB', completed.stderr)
    silence_duration = _silence_duration(completed.stderr, duration)
    return {
        'hasAudio': True,
        'durationSec': round(duration, 3),
        'codec': audio_stream.get('codec_name'),
        'channels': audio_stream.get('channels'),
        'sampleRate': int(audio_stream.get('sample_rate')) if str(audio_stream.get('sample_rate', '')).isdigit() else None,
        'silenceRatio': round(silence_duration / duration, 4) if duration > 0 else 0.0,
        'approximateLoudness': float(mean_volume_match.group(1)) if mean_volume_match else None,
        'speechPresent': None,
        'transcriptionStatus': 'not_attempted',
    }


def extract_audio_track(file_path: str, output_dir: str) -> str:
    output_path = Path(output_dir) / 'transcription_audio.mp3'
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', file_path,
        '-vn', '-ac', '1', '-ar', '16000', '-b:a', '64k', '-y', str(output_path),
    ]
    subprocess.check_call(command)
    return str(output_path)
