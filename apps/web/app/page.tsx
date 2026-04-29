'use client';
import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

const statusLabels: Record<string, string> = {
  queued: 'Видео в очереди',
  processing: 'Идёт анализ видео',
  done: 'Анализ готов',
  failed: 'Ошибка анализа'
};

const copyText = async (text: string | string[] | undefined | null) => {
  const value = Array.isArray(text) ? text.join(', ') : text || '';
  if (!value) return;
  await navigator.clipboard.writeText(value);
};

const CopyRow = ({ label, value }: { label: string; value: any }) => (
  <div className="border rounded p-2 space-y-1">
    <p className="text-sm font-medium">{label}</p>
    <p className="text-sm whitespace-pre-wrap">{Array.isArray(value) ? value.join(', ') : value || '—'}</p>
    <button className="text-xs bg-slate-800 text-white px-2 py-1 rounded" onClick={() => copyText(value)}>Скопировать</button>
  </div>
);

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
  const seoDraft = report?.seoDraft || {};
  const aiProviderUsed = report?.aiProviderUsed || 'mock';
  const aiFallbackUsed = Boolean(report?.aiFallbackUsed);
  const aiWarnings = report?.aiWarnings || [];

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
          <section><h2 className="text-lg font-semibold">Статус задачи</h2><p><b>{statusText}</b></p></section>
          {technical && <section><h2 className="text-lg font-semibold">Технические параметры</h2><ul className="list-disc ml-5"><li>Длительность: {technical.durationSec ?? '—'} сек.</li><li>Разрешение: {technical.resolution || '—'}</li><li>FPS: {technical.fps || '—'}</li><li>Соотношение сторон: {technical.aspectRatio || '—'}</li><li>Аудио: {technical.hasAudio ? 'Да' : 'Нет'}</li><li>Битрейт: {technical.bitrate || '—'}</li></ul></section>}
          <section><h2 className="text-lg font-semibold">Кадры из видео</h2>{frames.length === 0 ? <p>Кадры пока не готовы.</p> : <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{frames.map((f: any) => <div key={f.storageKey} className="border rounded p-2 text-xs space-y-1"><img src={`${API_URL}${f.previewUrl}`} alt={f.filename} className="w-full h-auto rounded" /><p>{f.filename}</p><p>~{f.approxTimeSec} сек</p></div>)}</div>}</section>
          {platformFit && <section><h2 className="text-lg font-semibold">Оценка платформ</h2><ul className="list-disc ml-5"><li>YouTube Shorts: {platformFit.youtubeShorts?.score ?? '—'}</li><li>YouTube Video: {platformFit.youtubeVideo?.score ?? '—'}</li><li>Instagram Reels: {platformFit.instagramReels?.score ?? '—'}</li><li>TikTok: {platformFit.tiktok?.score ?? '—'}</li></ul></section>}
          <section><h2 className="text-lg font-semibold">Проблемы</h2><ul className="list-disc ml-5">{issues.length === 0 ? <li>Критичных проблем не найдено.</li> : issues.map((issue: string, idx: number) => <li key={idx}>{issue}</li>)}</ul></section>
          <section><h2 className="text-lg font-semibold">Рекомендации</h2><ul className="list-disc ml-5">{recommendations.length === 0 ? <li>Базовых рекомендаций пока нет.</li> : recommendations.map((rec: string, idx: number) => <li key={idx}>{rec}</li>)}</ul></section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">AI генерация SEO</h2>
            <p className="text-sm text-slate-600">AI provider: {aiProviderUsed} · Fallback: {aiFallbackUsed ? 'yes' : 'no'}</p>
            {aiWarnings.length > 0 && (
              <ul className="list-disc ml-5 text-sm text-amber-700">
                {aiWarnings.map((warning: string, idx: number) => <li key={idx}>{warning}</li>)}
              </ul>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-semibold">SEO-пакеты по платформам</h2>
            {[
              ['youtubeVideo', 'YouTube видео'],
              ['youtubeShorts', 'YouTube Shorts'],
              ['instagramReels', 'Instagram Reels'],
              ['tiktok', 'TikTok']
            ].map(([key, title]) => {
              const data: any = seoDraft[key as string] || {};
              return (
                <div key={key} className="border rounded p-3 space-y-2">
                  <h3 className="font-semibold">{title}</h3>
                  <CopyRow label="Главный заголовок / текст" value={data.bestTitle || data.caption || '—'} />
                  {data.titleOptions && <div><p className="text-sm font-medium">Варианты заголовков</p><ul className="list-disc ml-5 text-sm">{data.titleOptions.map((t: string, i: number) => <li key={i}>{t}</li>)}</ul></div>}
                  <CopyRow label="Описание / caption" value={data.description || data.caption} />
                  <CopyRow label="Хештеги" value={data.hashtags} />
                  {data.tags && <CopyRow label="Теги" value={data.tags} />}
                  <CopyRow label="Текст обложки" value={data.coverText || data.thumbnailText} />
                  <CopyRow label="Закреплённый комментарий" value={data.pinnedComment} />
                  <div>
                    <p className="text-sm font-medium">Рекомендации</p>
                    <ul className="list-disc ml-5 text-sm">{(data.improvementTips || []).map((tip: string, i: number) => <li key={i}>{tip}</li>)}</ul>
                  </div>
                </div>
              );
            })}
          </section>
        </div>
      )}
    </main>
  );
}
