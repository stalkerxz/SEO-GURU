import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { randomUUID } from 'crypto';
import path from 'path';
import fs from 'fs';
import { Readable } from 'stream';
const { Pool } = require('pg');
import Redis from 'ioredis';
import { S3Client, PutObjectCommand, CreateBucketCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

const storageMode = process.env.STORAGE_MODE || 'local';
const localPath = process.env.LOCAL_STORAGE_PATH || './storage';
const minioBucket = process.env.MINIO_BUCKET || 'videos';
const maxFileSizeMb = Number(process.env.MAX_UPLOAD_SIZE_MB || 500);
const allowedExt = new Set(['.mp4', '.mov', '.webm', '.m4v']);
const allowedMime = new Set(['video/mp4', 'video/quicktime', 'video/webm', 'video/x-m4v']);
const safeFrameFileRegex = /^frame_\d{4}\.jpg$/;
const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const startupAttempts = 20;
const startupDelayMs = 2000;

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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const validateVideoFile = (file: Express.Multer.File) => {
  const ext = path.extname(file.originalname || '').toLowerCase();
  return allowedExt.has(ext) && allowedMime.has(file.mimetype);
};

const parseKeywords = (raw: string | undefined) =>
  (raw || '')
    .split(',')
    .map((keyword) => keyword.trim())
    .filter(Boolean);

const getUserContext = (body: Record<string, unknown>) => ({
  userGoal: typeof body.userGoal === 'string' && body.userGoal.trim() ? body.userGoal.trim() : 'views_and_reach',
  niche: typeof body.niche === 'string' && body.niche.trim() ? body.niche.trim() : 'general_video',
  language: typeof body.language === 'string' && body.language.trim() ? body.language.trim() : 'ru',
  geo: typeof body.geo === 'string' ? body.geo.trim() : '',
  brandName: typeof body.brandName === 'string' ? body.brandName.trim() : '',
  keywords: parseKeywords(typeof body.keywords === 'string' ? body.keywords : undefined)
});

const ensureDatabaseSchema = async () => {
  await pool.query('ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS analysis_report JSONB');
  await pool.query('ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS user_context JSONB');
};

const waitForDatabaseAndEnsureSchema = async () => {
  for (let attempt = 1; attempt <= startupAttempts; attempt += 1) {
    try {
      await ensureDatabaseSchema();
      return;
    } catch (error) {
      if (attempt === startupAttempts) throw error;
      console.warn('Database is not ready yet, retrying...', error);
      await sleep(startupDelayMs);
    }
  }
};

const ensureMinioBucket = async () => {
  for (let attempt = 1; attempt <= startupAttempts; attempt += 1) {
    try {
      await s3.send(new CreateBucketCommand({ Bucket: minioBucket }));
      return;
    } catch (error: any) {
      if (error?.name === 'BucketAlreadyOwnedByYou' || error?.name === 'BucketAlreadyExists') return;
      if (attempt === startupAttempts) throw error;
      console.warn('MinIO is not ready yet, retrying bucket init...', error);
      await sleep(startupDelayMs);
    }
  }
};

app.get('/health', (_, res) => res.json({ ok: true }));
app.post('/api/videos/upload', upload.single('video'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No video file provided' });
  if (!validateVideoFile(req.file)) return res.status(400).json({ error: 'Invalid file type. Allowed: mp4/mov/webm/m4v' });

  const userContext = getUserContext(req.body as Record<string, unknown>);
  const jobId = randomUUID();
  const originalFilename = req.file.originalname;
  const ext = path.extname(originalFilename).toLowerCase();
  const key = `videos/${jobId}${ext}`;

  if (storageMode === 'minio') {
    await s3.send(new PutObjectCommand({
      Bucket: minioBucket,
      Key: key,
      Body: req.file.buffer,
      ContentType: req.file.mimetype
    }));
  } else {
    const target = path.join(localPath, key);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, req.file.buffer);
  }

  await pool.query('INSERT INTO video_jobs (id, filename, storage_key, status, user_context) VALUES ($1, $2, $3, $4, $5)', [jobId, originalFilename, key, 'queued', JSON.stringify(userContext)]);
  await redis.lpush('video_jobs_queue', JSON.stringify({ id: jobId, storageKey: key }));
  res.json({ jobId, status: 'queued' });
});

app.get('/api/frames/:jobId/:filename', async (req, res) => {
  const { jobId, filename } = req.params;
  if (!uuidRegex.test(jobId)) return res.status(400).json({ error: 'Invalid job id' });
  if (!safeFrameFileRegex.test(filename)) return res.status(400).json({ error: 'Invalid frame filename' });

  const frameKey = `frames/${jobId}/${filename}`;
  try {
    if (storageMode === 'minio') {
      const data = await s3.send(new GetObjectCommand({ Bucket: minioBucket, Key: frameKey }));
      if (!data.Body) return res.status(404).json({ error: 'Frame not found' });
      if (!(data.Body instanceof Readable)) return res.status(500).json({ error: 'Invalid frame stream' });
      res.setHeader('Content-Type', 'image/jpeg');
      data.Body.pipe(res);
      return;
    }

    const framePath = path.join(localPath, frameKey);
    if (!fs.existsSync(framePath)) return res.status(404).json({ error: 'Frame not found' });
    return res.sendFile(path.resolve(framePath));
  } catch (_e) {
    return res.status(404).json({ error: 'Frame not found' });
  }
});

app.get('/api/jobs/:id', async (req, res) => {
  const result = await pool.query('SELECT * FROM video_jobs WHERE id = $1', [req.params.id]);
  if (!result.rows[0]) return res.status(404).json({ error: 'Job not found' });
  res.json(result.rows[0]);
});

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  if (err?.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ error: `File too large. Max ${maxFileSizeMb}MB` });
  return res.status(500).json({ error: 'Upload failed' });
});

const port = Number(process.env.API_PORT || 4000);

const bootstrap = async () => {
  try {
    await waitForDatabaseAndEnsureSchema();
    if (storageMode === 'minio') await ensureMinioBucket();
    app.listen(port, () => console.log(`API running on ${port}`));
  } catch (error) {
    console.error('API startup failed: dependencies are not ready.', error);
    process.exit(1);
  }
};

bootstrap();
