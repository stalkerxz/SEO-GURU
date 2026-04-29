import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import boto3
import psycopg2
import redis

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


def upload_frame(s3, frame_path: Path, job_id: str, idx: int):
    key = f'frames/{job_id}/frame_{idx:04d}.jpg'
    s3.upload_file(str(frame_path), MINIO_BUCKET, key)
    return {'index': idx, 'storageKey': key, 'filename': frame_path.name}


def persist_local_frame(frame_path: Path, job_id: str, idx: int):
    rel_key = f'frames/{job_id}/frame_{idx:04d}.jpg'
    target = Path(LOCAL_STORAGE_PATH) / rel_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(frame_path.read_bytes())
    return {'index': idx, 'storageKey': rel_key, 'filename': frame_path.name}


def analyze_file(file_path: str, job_id: str):
    meta = ffprobe_json(file_path)
    vstream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'video'), {})
    astream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'audio'), None)
    duration = float(meta.get('format', {}).get('duration', 0) or 0)
    width = vstream.get('width', 0)
    height = vstream.get('height', 0)

    with tempfile.TemporaryDirectory() as d:
        frame_files = extract_frames(file_path, d, duration)
        frames = []
        if STORAGE_MODE == 'minio':
            s3 = boto3.client(
                's3',
                endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT', 'minio')}:{os.getenv('MINIO_PORT', '9000')}",
                aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minio'),
                aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minio123')
            )
            for i, f in enumerate(frame_files, start=1):
                frames.append(upload_frame(s3, f, job_id, i))
        else:
            for i, f in enumerate(frame_files, start=1):
                frames.append(persist_local_frame(f, job_id, i))

    return {
        'duration': duration,
        'resolution': f'{width}x{height}' if width and height else None,
        'fps': vstream.get('r_frame_rate'),
        'codec': vstream.get('codec_name'),
        'bitrate': meta.get('format', {}).get('bit_rate'),
        'aspect_ratio': f"{width}:{height}" if width and height else None,
        'has_audio': astream is not None,
        'frames': frames,
    }


def update_job(job_id, status, result=None, error=None):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    frames = result.get('frames') if result else None
    cur.execute(
        'UPDATE video_jobs SET status=%s, result=%s, frames=%s, error=%s, updated_at=NOW() WHERE id=%s',
        (status, json.dumps(result) if result else None, json.dumps(frames) if frames else None, error, job_id)
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
        result = analyze_file(load_video(payload['storageKey']), job_id)
        update_job(job_id, 'done', result=result)
    except Exception as e:
        update_job(job_id, 'failed', error=str(e))


if __name__ == '__main__':
    while True:
        consume_once()
        time.sleep(1)
