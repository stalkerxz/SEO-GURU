'use client';
import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

const statusLabels: Record<string, string> = {
  queued: 'Видео в очереди',
  processing: 'Идёт анализ видео',
  done: 'Анализ готов',
  failed: 'Ошибка анализа'
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async () => {
    if (!file) return;
    setError(null);
    setJob(null);
    const form = new FormData();
    form.append('video', file);
    const response = await fetch(`${API_URL}/api/videos/upload`, { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) {
      setError(data.error || 'Не удалось загрузить видео');
      return;
    }
    setJobId(data.jobId);
  };

  const refresh = async (targetJobId?: string) => {
    const id = targetJobId || jobId;
    if (!id) return;
    const response = await fetch(`${API_URL}/api/jobs/${id}`);
    const data = await response.json();
    setJob(data);
    if (!response.ok) setError(data.error || 'Не удалось получить статус задачи');
  };

  useEffect(() => {
    if (!jobId) return;
    refresh(jobId);
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !job) return;
    if (job.status === 'done' || job.status === 'failed') return;
    const id = setInterval(() => refresh(jobId), 2000);
    return () => clearInterval(id);
  }, [jobId, job?.status]);

  const frames = job?.frames || [];
  const report = job?.analysis_report;
  const technical = report?.technical;
  const platformFit = report?.platformFit;
  const statusText = useMemo(() => (job?.status ? statusLabels[job.status] || job.status : null), [job?.status]);
  const issues = report?.detectedIssues || [];
  const recommendations = report?.recommendations || [];

  return (
    <main className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Video SEO Analyzer</h1>
      <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <div className="flex gap-2">
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={upload}>Upload</button>
        <button className="bg-slate-700 text-white px-4 py-2 rounded" onClick={() => refresh()} disabled={!jobId}>Refresh status</button>
      </div>

      {jobId && <p>Job ID: {jobId}</p>}
      {error && <p className="text-red-600">{error}</p>}

      {job && (
        <div className="bg-white rounded p-4 shadow space-y-6">
          <section>
            <h2 className="text-lg font-semibold">Статус задачи</h2>
            <p><b>{statusText}</b></p>
            {job.status === 'failed' && <p className="text-red-600">{job.error || 'Произошла ошибка анализа видео.'}</p>}
          </section>

          {job.status === 'done' && !report && <p className="text-amber-700">Отчёт анализа пока не сформирован.</p>}

          {technical && (
            <section>
              <h2 className="text-lg font-semibold">Технические параметры</h2>
              <ul className="list-disc ml-5">
                <li>Длительность: {technical.durationSec ?? '—'} сек.</li>
                <li>Разрешение: {technical.resolution || '—'}</li>
                <li>FPS: {technical.fps || '—'}</li>
                <li>Соотношение сторон: {technical.aspectRatio || '—'}</li>
                <li>Аудио: {technical.hasAudio ? 'Да' : 'Нет'}</li>
                <li>Битрейт: {technical.bitrate || '—'}</li>
              </ul>
            </section>
          )}

          <section>
            <h2 className="text-lg font-semibold">Кадры из видео</h2>
            {frames.length === 0 ? <p>Кадры пока не готовы.</p> : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {frames.map((f: any) => (
                  <div key={f.storageKey} className="border rounded p-2 text-xs space-y-1">
                    <img src={`${API_URL}${f.previewUrl}`} alt={f.filename} className="w-full h-auto rounded" />
                    <p>{f.filename}</p>
                    <p>~{f.approxTimeSec} сек</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {platformFit && (
            <section>
              <h2 className="text-lg font-semibold">Оценка платформ</h2>
              <ul className="list-disc ml-5">
                <li>YouTube Shorts: {platformFit.youtubeShorts?.score ?? '—'}</li>
                <li>YouTube Video: {platformFit.youtubeVideo?.score ?? '—'}</li>
                <li>Instagram Reels: {platformFit.instagramReels?.score ?? '—'}</li>
                <li>TikTok: {platformFit.tiktok?.score ?? '—'}</li>
              </ul>
            </section>
          )}

          <section>
            <h2 className="text-lg font-semibold">Проблемы</h2>
            <ul className="list-disc ml-5">
              {issues.length === 0 ? <li>Критичных проблем не найдено.</li> : issues.map((issue: string, idx: number) => <li key={idx}>{issue}</li>)}
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">Рекомендации</h2>
            <ul className="list-disc ml-5">
              {recommendations.length === 0 ? <li>Базовых рекомендаций пока нет.</li> : recommendations.map((rec: string, idx: number) => <li key={idx}>{rec}</li>)}
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">SEO-заготовка</h2>
            <pre className="bg-slate-100 p-3 rounded overflow-auto text-xs">{JSON.stringify(report?.seoDraft || {}, null, 2)}</pre>
          </section>

          <details>
            <summary className="cursor-pointer text-sm font-medium">Показать технический JSON</summary>
            <pre className="bg-slate-900 text-green-300 p-3 rounded overflow-auto text-xs mt-2">{JSON.stringify(job, null, 2)}</pre>
          </details>
        </div>
      )}
    </main>
  );
}
