import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { randomUUID } from 'crypto';
import path from 'path';
import fs from 'fs';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { S3Client, PutObjectCommand, CreateBucketCommand } from '@aws-sdk/client-s3';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

const storageMode = process.env.STORAGE_MODE || 'local';
const localPath = process.env.LOCAL_STORAGE_PATH || './storage';
const maxFileSizeMb = Number(process.env.MAX_UPLOAD_SIZE_MB || 500);
const allowedExt = new Set(['.mp4', '.mov', '.webm', '.m4v']);
const allowedMime = new Set(['video/mp4', 'video/quicktime', 'video/webm', 'video/x-m4v']);

if (!fs.existsSync(localPath)) fs.mkdirSync(localPath, { recursive: true });

const s3 = new S3Client({
  region: 'us-east-1',
  endpoint: `http://${process.env.MINIO_ENDPOINT}:${process.env.MINIO_PORT}`,
  forcePathStyle: true,
  credentials: {
    accessKeyId: process.env.MINIO_ACCESS_KEY || 'minio',
    secretAccessKey: process.env.MINIO_SECRET_KEY || 'minio123'
  }
});

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: maxFileSizeMb * 1024 * 1024 }
});

const validateVideoFile = (file: Express.Multer.File) => {
  const ext = path.extname(file.originalname || '').toLowerCase();
  return allowedExt.has(ext) && allowedMime.has(file.mimetype);
};

app.get('/health', (_, res) => res.json({ ok: true }));

app.post('/api/videos/upload', upload.single('video'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No video file provided' });
  if (!validateVideoFile(req.file)) return res.status(400).json({ error: 'Invalid file type. Allowed: mp4/mov/webm/m4v' });

  const jobId = randomUUID();
  const originalFilename = req.file.originalname;
  const ext = path.extname(originalFilename).toLowerCase();
  const key = `videos/${jobId}${ext}`;

  if (storageMode === 'minio') {
    await s3.send(new PutObjectCommand({
      Bucket: process.env.MINIO_BUCKET,
      Key: key,
      Body: req.file.buffer,
      ContentType: req.file.mimetype
    }));
  } else {
    const target = path.join(localPath, key);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, req.file.buffer);
  }

  await pool.query(
    'INSERT INTO video_jobs (id, filename, storage_key, status) VALUES ($1, $2, $3, $4)',
    [jobId, originalFilename, key, 'queued']
  );

  await redis.lpush('video_jobs_queue', JSON.stringify({ id: jobId, storageKey: key }));
  res.json({ jobId, status: 'queued' });
});

app.get('/api/jobs/:id', async (req, res) => {
  const result = await pool.query('SELECT * FROM video_jobs WHERE id = $1', [req.params.id]);
  if (!result.rows[0]) return res.status(404).json({ error: 'Job not found' });
  res.json(result.rows[0]);
});

(async () => {
  if (storageMode === 'minio') {
    try {
      await s3.send(new CreateBucketCommand({ Bucket: process.env.MINIO_BUCKET }));
    } catch (e) {}
  }
})();


app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  if (err?.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ error: `File too large. Max ${maxFileSizeMb}MB` });
  return res.status(500).json({ error: 'Upload failed' });
});

const port = Number(process.env.API_PORT || 4000);
app.listen(port, () => console.log(`API running on ${port}`));
