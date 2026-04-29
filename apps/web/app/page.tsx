'use client';
import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

const statusLabels: Record<string, string> = {
  queued: 'Видео в очереди',
  processing: 'Идёт анализ видео',
  done: 'Анализ готов',
  failed: 'Ошибка анализа'
};

const goals = ['views_and_reach', 'subscribers', 'leads', 'portfolio', 'sales'];
const niches = ['auto', 'real_estate', 'travel', 'expert_content', 'music_event', 'beauty', 'food', 'education', 'general_video'];
const languages = ['ru', 'en'];

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

const AnalysisContextBlock = ({ aiInput }: { aiInput: any }) => (
  <section>
    <h2 className="text-lg font-semibold">Контекст анализа</h2>
    <ul className="list-disc ml-5">
      <li>Цель: {aiInput?.userGoal || '—'}</li>
      <li>Ниша: {aiInput?.niche || '—'}</li>
      <li>Язык: {aiInput?.language || '—'}</li>
      <li>Гео: {aiInput?.geo || '—'}</li>
      <li>Бренд: {aiInput?.brandName || '—'}</li>
      <li>Ключевые слова: {(aiInput?.keywords || []).join(', ') || '—'}</li>
    </ul>
  </section>
);

const TechnicalBlock = ({ technical }: { technical: any }) => technical && (
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
);

const FramesBlock = ({ frames }: { frames: any[] }) => (
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
);

const PlatformFitBlock = ({ platformFit }: { platformFit: any }) => platformFit && (
  <section>
    <h2 className="text-lg font-semibold">Оценка платформ</h2>
    <ul className="list-disc ml-5">
      <li>YouTube Shorts: {platformFit.youtubeShorts?.score ?? '—'}</li>
      <li>YouTube Video: {platformFit.youtubeVideo?.score ?? '—'}</li>
      <li>Instagram Reels: {platformFit.instagramReels?.score ?? '—'}</li>
      <li>TikTok: {platformFit.tiktok?.score ?? '—'}</li>
    </ul>
  </section>
);

const SeoPlatformCard = ({ title, data }: { title: string; data: any }) => {
  const copyWholePackage = async () => {
    const payload = [
      `Заголовок: ${data.bestTitle || data.caption || ''}`,
      `Варианты заголовков: ${(data.titleOptions || []).join(' | ')}`,
      `Описание: ${data.description || data.caption || ''}`,
      `Хештеги: ${(data.hashtags || []).join(' ')}`,
      data.tags ? `Теги: ${data.tags.join(', ')}` : '',
      `Закреплённый комментарий: ${data.pinnedComment || ''}`,
      `Текст обложки: ${data.coverText || data.thumbnailText || ''}`
    ].filter(Boolean).join('\n\n');
    await navigator.clipboard.writeText(payload);
  };

  return (
    <div className="border rounded p-3 space-y-2">
      <h3 className="font-semibold">{title}</h3>
      <button className="text-xs bg-black text-white px-2 py-1 rounded" onClick={copyWholePackage}>Скопировать весь SEO-пакет</button>
      <CopyRow label="Главный заголовок / текст" value={data.bestTitle || data.caption || '—'} />
      {data.titleOptions && (
        <div>
          <p className="text-sm font-medium">Варианты заголовков</p>
          <ul className="list-disc ml-5 text-sm">
            {data.titleOptions.map((t: string, i: number) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      )}
      <CopyRow label="Описание / caption" value={data.description || data.caption} />
      <CopyRow label="Хештеги" value={data.hashtags} />
      {data.tags && <CopyRow label="Теги" value={data.tags} />}
      <CopyRow label="Текст обложки" value={data.coverText || data.thumbnailText} />
      <CopyRow label="Закреплённый комментарий" value={data.pinnedComment} />
      <div>
        <p className="text-sm font-medium">Рекомендации</p>
        <ul className="list-disc ml-5 text-sm">
          {(data.improvementTips || []).map((tip: string, i: number) => <li key={i}>{tip}</li>)}
        </ul>
      </div>
    </div>
  );
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [contextForm, setContextForm] = useState({ userGoal: 'views_and_reach', niche: 'general_video', language: 'ru', geo: '', brandName: '', keywords: '' });

  const upload = async () => {
    if (!file) return;
    setError(null);
    setJob(null);
    const form = new FormData();
    form.append('video', file);
    Object.entries(contextForm).forEach(([key, value]) => form.append(key, value));
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

  useEffect(() => { if (jobId) refresh(jobId); }, [jobId]);
  useEffect(() => {
    if (!jobId || !job || job.status === 'done' || job.status === 'failed') return;
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
  const aiInput = report?.ai_input || {};

  return (
    <main className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Video SEO Analyzer</h1>

      <section className="border rounded p-3 space-y-2">
        <h2 className="text-lg font-semibold">Настройки анализа перед загрузкой</h2>
        <div className="grid md:grid-cols-2 gap-2">
          <label className="text-sm">Цель публикации<select className="w-full border rounded p-2" value={contextForm.userGoal} onChange={(e) => setContextForm((prev) => ({ ...prev, userGoal: e.target.value }))}>{goals.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="text-sm">Ниша<select className="w-full border rounded p-2" value={contextForm.niche} onChange={(e) => setContextForm((prev) => ({ ...prev, niche: e.target.value }))}>{niches.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="text-sm">Язык<select className="w-full border rounded p-2" value={contextForm.language} onChange={(e) => setContextForm((prev) => ({ ...prev, language: e.target.value }))}>{languages.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="text-sm">Гео<input className="w-full border rounded p-2" placeholder="Тюмень" value={contextForm.geo} onChange={(e) => setContextForm((prev) => ({ ...prev, geo: e.target.value }))} /></label>
          <label className="text-sm">Бренд / автор<input className="w-full border rounded p-2" placeholder="PROTOPOPOV PRODUCTION" value={contextForm.brandName} onChange={(e) => setContextForm((prev) => ({ ...prev, brandName: e.target.value }))} /></label>
          <label className="text-sm md:col-span-2">Ключевые слова<input className="w-full border rounded p-2" placeholder="BMW X5, авто съёмка, cinematic car edit" value={contextForm.keywords} onChange={(e) => setContextForm((prev) => ({ ...prev, keywords: e.target.value }))} /></label>
        </div>
      </section>

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
          <AnalysisContextBlock aiInput={aiInput} />
          <TechnicalBlock technical={technical} />
          <FramesBlock frames={frames} />
          <PlatformFitBlock platformFit={platformFit} />
          <section><h2 className="text-lg font-semibold">Проблемы</h2><ul className="list-disc ml-5">{issues.length === 0 ? <li>Критичных проблем не найдено.</li> : issues.map((issue: string, idx: number) => <li key={idx}>{issue}</li>)}</ul></section>
          <section><h2 className="text-lg font-semibold">Рекомендации</h2><ul className="list-disc ml-5">{recommendations.length === 0 ? <li>Базовых рекомендаций пока нет.</li> : recommendations.map((rec: string, idx: number) => <li key={idx}>{rec}</li>)}</ul></section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">AI генерация SEO</h2>
            <p className="text-sm text-slate-600">AI provider: {aiProviderUsed} · Fallback: {aiFallbackUsed ? 'yes' : 'no'}</p>
            {aiWarnings.length > 0 && <ul className="list-disc ml-5 text-sm text-amber-700">{aiWarnings.map((warning: string, idx: number) => <li key={idx}>{warning}</li>)}</ul>}
          </section>

          <section className="space-y-4">
            <h2 className="text-lg font-semibold">SEO-пакеты по платформам</h2>
            {[
              ['youtubeVideo', 'YouTube видео'],
              ['youtubeShorts', 'YouTube Shorts'],
              ['instagramReels', 'Instagram Reels'],
              ['tiktok', 'TikTok']
            ].map(([key, title]) => <SeoPlatformCard key={key} title={title} data={seoDraft[key as string] || {}} />)}
          </section>
        </div>
      )}
    </main>
  );
}
