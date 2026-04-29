import json
import os
import subprocess
from pathlib import Path
import tempfile
import psycopg2
import redis
import boto3
from fastapi import FastAPI

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://video:video@localhost:5432/video_seo')
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', '/app/storage')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'videos')

r = redis.from_url(REDIS_URL)
app = FastAPI()


def ffprobe_json(file_path: str):
    cmd = ['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', file_path]
    out = subprocess.check_output(cmd).decode('utf-8')
    return json.loads(out)


def extract_frames(file_path: str, out_dir: str, duration: float):
    if duration <= 60:
        fps = '1/5'
    elif duration <= 300:
        fps = '1/10'
    else:
        fps = '1/20'
    pattern = str(Path(out_dir) / 'frame_%04d.jpg')
    subprocess.check_call(['ffmpeg', '-i', file_path, '-vf', f'fps={fps}', '-q:v', '2', pattern, '-y'])
    return sorted([str(Path(out_dir) / f) for f in os.listdir(out_dir) if f.endswith('.jpg')])


def analyze_file(file_path: str):
    meta = ffprobe_json(file_path)
    vstream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'video'), {})
    astream = next((s for s in meta.get('streams', []) if s.get('codec_type') == 'audio'), None)
    duration = float(meta.get('format', {}).get('duration', 0) or 0)
    width = vstream.get('width', 0)
    height = vstream.get('height', 0)
    ratio = f"{width}:{height}" if width and height else None

    with tempfile.TemporaryDirectory() as d:
        frames = extract_frames(file_path, d, duration)
        return {
            'duration': duration,
            'resolution': f'{width}x{height}' if width and height else None,
            'fps': vstream.get('r_frame_rate'),
            'codec': vstream.get('codec_name'),
            'bitrate': meta.get('format', {}).get('bit_rate'),
            'aspect_ratio': ratio,
            'has_audio': astream is not None,
            'frames': frames,
        }


def update_job(job_id, status, result=None, error=None):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "UPDATE video_jobs SET status=%s, result=%s, frames=%s, error=%s, updated_at=NOW() WHERE id=%s",
        (status, json.dumps(result) if result else None, json.dumps(result.get('frames')) if result else None, error, job_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def load_video(storage_key: str) -> str:
    local_target = Path(tempfile.gettempdir()) / storage_key
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
        return {'processed': False}
    payload = json.loads(item[1])
    job_id = payload['id']
    try:
        update_job(job_id, 'processing')
        file_path = load_video(payload['storageKey'])
        result = analyze_file(file_path)
        update_job(job_id, 'done', result=result)
        return {'processed': True, 'job_id': job_id}
    except Exception as e:
        update_job(job_id, 'failed', error=str(e))
        return {'processed': True, 'job_id': job_id, 'error': str(e)}


@app.get('/health')
def health():
    return {'ok': True}


@app.post('/consume')
def consume():
    return consume_once()


if __name__ == '__main__':
    import time
    while True:
        consume_once()
        time.sleep(1)
