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

dotenv.config({ path: '/app/.env.example' });

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

const storageMode = process.env.STORAGE_MODE || 'local';
const localPath = process.env.LOCAL_STORAGE_PATH || './storage';
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

const upload = multer({ storage: multer.memoryStorage() });

app.get('/health', (_, res) => res.json({ ok: true }));

app.post('/api/videos/upload', upload.single('video'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No video file provided' });
  const jobId = randomUUID();
  const filename = req.file.originalname;
  const key = `${jobId}-${filename}`;

  if (storageMode === 'minio') {
    await s3.send(new PutObjectCommand({
      Bucket: process.env.MINIO_BUCKET,
      Key: key,
      Body: req.file.buffer,
      ContentType: req.file.mimetype
    }));
  } else {
    fs.writeFileSync(path.join(localPath, key), req.file.buffer);
  }

  await pool.query(
    'INSERT INTO video_jobs (id, filename, storage_key, status) VALUES ($1, $2, $3, $4)',
    [jobId, filename, key, 'queued']
  );

  await redis.lpush('video_jobs_queue', JSON.stringify({ id: jobId, storageKey: key }));

  res.json({ jobId, status: 'queued' });
});

app.get('/api/jobs/:id', async (req, res) => {
  const result = await pool.query('SELECT * FROM video_jobs WHERE id = $1', [req.params.id]);
  if (!result.rows[0]) return res.status(404).json({ error: 'Job not found' });
  res.json(result.rows[0]);
});

const port = Number(process.env.API_PORT || 4000);
app.listen(port, () => console.log(`API running on ${port}`));


(async () => {
  if (storageMode === 'minio') {
    try {
      await s3.send(new CreateBucketCommand({ Bucket: process.env.MINIO_BUCKET }));
    } catch (e) {}
  }
})();
