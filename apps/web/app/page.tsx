'use client';

import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

const statusLabels: Record<string, string> = {
  queued: 'Видео в очереди',
  processing: 'Идёт анализ',
  done: 'Анализ готов',
  failed: 'Ошибка анализа'
};

const goalOptions = [
  { value: 'views_and_reach', label: 'Охваты и просмотры' },
  { value: 'subscribers', label: 'Подписчики' },
  { value: 'leads', label: 'Заявки / клиенты' },
  { value: 'portfolio', label: 'Портфолио' },
  { value: 'sales', label: 'Продажи' }
];

const nicheOptions = [
  { value: 'auto', label: 'Авто' },
  { value: 'real_estate', label: 'Недвижимость' },
  { value: 'travel', label: 'Путешествия' },
  { value: 'expert_content', label: 'Экспертный контент' },
  { value: 'music_event', label: 'Музыка / мероприятия' },
  { value: 'beauty', label: 'Beauty' },
  { value: 'food', label: 'Еда' },
  { value: 'education', label: 'Образование' },
  { value: 'general_video', label: 'Общее видео' }
];

const languageOptions = [
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'Английский' }
];

const cn = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(' ');

const scoreLabel = (score: number) => {
  if (score >= 80) return 'Отлично подходит';
  if (score >= 60) return 'Хороший потенциал';
  if (score >= 40) return 'Нужна адаптация';
  return 'Слабое соответствие';
};

const cardClass = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm';

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      disabled={!text}
      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {copied ? 'Скопировано' : 'Скопировать'}
    </button>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">{value || '—'}</p>
    </div>
  );
}

function PlatformScoreCard({ title, score }: { title: string; score: number }) {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <p className="text-sm text-slate-600">{title}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{safeScore}</p>
      <div className="mt-3 h-2 w-full rounded-full bg-slate-100" aria-hidden>
        <div className="h-2 rounded-full bg-blue-500" style={{ width: `${safeScore}%` }} />
      </div>
      <p className="mt-2 text-xs text-slate-500">{scoreLabel(safeScore)}</p>
    </article>
  );
}

function EmptyState() {
  return (
    <section className={cn(cardClass, 'text-center')}>
      <h2 className="text-lg font-semibold text-slate-900">Загрузите видео для анализа</h2>
      <p className="mt-2 text-sm text-slate-600">После запуска анализа здесь появятся оценка платформ, проблемы, рекомендации и SEO-пакеты.</p>
    </section>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [contextForm, setContextForm] = useState({ userGoal: 'views_and_reach', niche: 'general_video', language: 'ru', geo: '', brandName: '', keywords: '' });

  const upload = async () => {
    if (!file || isUploading) return;
    setIsUploading(true);
    setError(null);
    setJob(null);
    const form = new FormData();
    form.append('video', file);
    Object.entries(contextForm).forEach(([key, value]) => form.append(key, value));

    try {
      const response = await fetch(`${API_URL}/api/videos/upload`, { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || 'Не удалось загрузить видео');
        return;
      }
      setJobId(data.jobId);
    } catch {
      setError('Ошибка сети при загрузке видео');
    } finally {
      setIsUploading(false);
    }
  };

  const refresh = async (targetJobId?: string) => {
    const id = targetJobId || jobId;
    if (!id || isRefreshing) return;
    setIsRefreshing(true);
    try {
      const response = await fetch(`${API_URL}/api/jobs/${id}`);
      const data = await response.json();
      setJob(data);
      if (!response.ok) setError(data.error || 'Не удалось получить статус задачи');
    } catch {
      setError('Ошибка сети при получении статуса');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => { if (jobId) refresh(jobId); }, [jobId]);
  useEffect(() => {
    if (!jobId || !job || job.status === 'done' || job.status === 'failed') return;
    const id = setInterval(() => refresh(jobId), 2500);
    return () => clearInterval(id);
  }, [jobId, job?.status]);

  const report = job?.analysis_report;
  const frames = job?.frames || [];
  const statusText = useMemo(() => (job?.status ? statusLabels[job.status] || job.status : null), [job?.status]);
  const issues = report?.detectedIssues || [];
  const recommendations = report?.recommendations || [];
  const platformFit = report?.platformFit || {};
  const seoDraft = report?.seoDraft || {};
  const aiInput = report?.ai_input || {};
  const fallbackContext = job?.user_context || {};
  const contextSource = {
    ...fallbackContext,
    ...aiInput,
    brandName: aiInput?.brandName || fallbackContext?.brandName || '',
    keywords: Array.isArray(aiInput?.keywords) && aiInput.keywords.length > 0
      ? aiInput.keywords
      : fallbackContext?.keywords || []
  };
  const technical = report?.technical || {};

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="flex items-start justify-between">
          <div>
            <p className="text-2xl font-bold tracking-tight">SEO-GURU</p>
            <p className="mt-1 text-sm text-slate-600">AI-анализ видео и SEO для YouTube, Shorts, Reels и TikTok</p>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">MVP / Local demo</span>
        </header>

        <section className={cardClass}>
          <h1 className="text-2xl font-semibold sm:text-3xl">Загрузите видео — получите SEO-пакеты под платформы</h1>
          <p className="mt-3 text-sm text-slate-600 sm:text-base">Сервис анализирует ролик, кадры, формат и контекст публикации, а затем готовит тексты для YouTube, Shorts, Instagram Reels и TikTok.</p>
          <ul className="mt-4 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
            <li>• Анализ видео</li>
            <li>• SEO под площадки</li>
            <li>• Рекомендации по улучшению</li>
            <li>• Копирование готовых текстов</li>
          </ul>
        </section>

        <section className={cardClass}>
          <h2 className="text-lg font-semibold">Настройки анализа</h2>
          <p className="mt-1 text-sm text-slate-500">Заполните контекст публикации перед загрузкой видео.</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {[{ id: 'goal', label: 'Цель публикации', key: 'userGoal', options: goalOptions, help: 'Выберите приоритет для продвижения.' }, { id: 'niche', label: 'Ниша', key: 'niche', options: nicheOptions, help: 'Тематика контента для более точных рекомендаций.' }, { id: 'language', label: 'Язык', key: 'language', options: languageOptions, help: 'Язык для генерации SEO-текстов.' }].map((field: any) => (
              <label key={field.id} htmlFor={field.id} className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">{field.label}</span>
                <select id={field.id} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" value={(contextForm as any)[field.key]} onChange={(e) => setContextForm((prev: any) => ({ ...prev, [field.key]: e.target.value }))}>
                  {field.options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <span className="text-xs text-slate-500">{field.help}</span>
              </label>
            ))}

            <label htmlFor="geo" className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Гео</span>
              <input id="geo" className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="Москва" value={contextForm.geo} onChange={(e) => setContextForm((prev) => ({ ...prev, geo: e.target.value }))} />
              <span className="text-xs text-slate-500">Город или регион целевой аудитории.</span>
            </label>

            <label htmlFor="brandName" className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Бренд / автор</span>
              <input id="brandName" className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="Имя бренда или автора" value={contextForm.brandName} onChange={(e) => setContextForm((prev) => ({ ...prev, brandName: e.target.value }))} />
              <span className="text-xs text-slate-500">Помогает адаптировать tone of voice.</span>
            </label>

            <label htmlFor="keywords" className="space-y-1 text-sm sm:col-span-2">
              <span className="font-medium text-slate-700">Ключевые слова</span>
              <input id="keywords" className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="например: авто обзор, cinematic" value={contextForm.keywords} onChange={(e) => setContextForm((prev) => ({ ...prev, keywords: e.target.value }))} />
              <span className="text-xs text-slate-500">Через запятую: темы, продукты, ключевые фразы.</span>
            </label>

            <label htmlFor="video" className="space-y-1 text-sm sm:col-span-2">
              <span className="font-medium text-slate-700">Видео файл</span>
              <input id="video" type="file" accept="video/*" className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <span className="text-xs text-slate-500">Поддерживаются распространённые видеоформаты.</span>
            </label>
          </div>

          <button onClick={upload} disabled={!file || isUploading} className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:bg-blue-300">
            {isUploading ? 'Загрузка…' : 'Проанализировать видео'}
          </button>
        </section>

        {jobId && (
          <section className={cardClass}>
            <p className="text-xs text-slate-500">Job ID: {jobId}</p>
            <p className="mt-1 text-sm">Статус: <span className="font-semibold">{statusText || '—'}</span></p>
            <button onClick={() => refresh()} disabled={!jobId || isRefreshing} className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">
              {isRefreshing ? 'Обновление…' : 'Обновить статус'}
            </button>
          </section>
        )}

        {error && <section className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">{error}</section>}
        {!job && !error && <EmptyState />}

        {job && report && (
          <section className="grid gap-4">
            <article className={cardClass}><h2 className="text-lg font-semibold">Контекст анализа</h2><div className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><MetricCard label="Цель" value={contextSource.userGoal || 'Не указано'} /><MetricCard label="Ниша" value={contextSource.niche || 'Не указано'} /><MetricCard label="Язык" value={contextSource.language || 'Не указано'} /><MetricCard label="Гео" value={contextSource.geo || 'Не указано'} /><MetricCard label="Бренд" value={contextSource.brandName || 'Не указано'} /><MetricCard label="Ключевые слова" value={(contextSource.keywords || []).join(', ') || 'Не указано'} /></div></article>

            <article className={cardClass}><h2 className="text-lg font-semibold">Технические параметры</h2><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><MetricCard label="Длительность" value={technical.durationSec ? `${technical.durationSec} сек` : '—'} /><MetricCard label="Разрешение" value={technical.resolution || '—'} /><MetricCard label="FPS" value={technical.fps ? String(technical.fps) : '—'} /><MetricCard label="Соотношение сторон" value={technical.aspectRatio || '—'} /><MetricCard label="Аудио" value={technical.hasAudio ? 'Да' : 'Нет'} /><MetricCard label="Битрейт" value={technical.bitrate || '—'} /></div></article>

            <article className={cardClass}><h2 className="text-lg font-semibold">Кадры из видео</h2>{frames.length === 0 ? <p className="mt-2 text-sm text-slate-500">Кадры пока не готовы.</p> : <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">{frames.map((f: any) => <div key={f.storageKey} className="overflow-hidden rounded-xl border border-slate-200 bg-white"><img src={`${API_URL}${f.previewUrl}`} alt={`Кадр ${f.filename}`} className="h-28 w-full object-cover" /><div className="p-2"><p className="truncate text-xs text-slate-500">{f.filename}</p><span className="mt-1 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700">~{f.approxTimeSec} сек</span></div></div>)}</div>}</article>

            <article className={cardClass}><h2 className="text-lg font-semibold">Оценка платформ</h2><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><PlatformScoreCard title="YouTube Shorts" score={platformFit.youtubeShorts?.score ?? 0} /><PlatformScoreCard title="YouTube Video" score={platformFit.youtubeVideo?.score ?? 0} /><PlatformScoreCard title="Instagram Reels" score={platformFit.instagramReels?.score ?? 0} /><PlatformScoreCard title="TikTok" score={platformFit.tiktok?.score ?? 0} /></div></article>

            <article className={cardClass}><h2 className="text-lg font-semibold">Проблемы</h2><ul className="mt-2 space-y-2 text-sm text-slate-700">{issues.length === 0 ? <li>Критичных проблем не найдено.</li> : issues.map((issue: string, idx: number) => <li key={idx} className="rounded-lg bg-slate-50 px-3 py-2">{issue}</li>)}</ul></article>

            <article className={cardClass}><h2 className="text-lg font-semibold">Рекомендации</h2><ul className="mt-2 space-y-2 text-sm text-slate-700">{recommendations.length === 0 ? <li>Базовых рекомендаций пока нет.</li> : recommendations.map((rec: string, idx: number) => <li key={idx} className="rounded-lg bg-slate-50 px-3 py-2">{rec}</li>)}</ul></article>

            <article className={cardClass}><h2 className="text-lg font-semibold">AI генерация SEO</h2><p className="mt-2 text-sm text-slate-600">Провайдер: {report.aiProviderUsed || 'mock'} · Fallback: {report.aiFallbackUsed ? 'Да' : 'Нет'}</p>{(report.aiWarnings || []).length > 0 && <ul className="mt-2 space-y-1 text-sm text-amber-700">{report.aiWarnings.map((warning: string, idx: number) => <li key={idx}>• {warning}</li>)}</ul>}</article>

            <article className={cardClass}><h2 className="text-lg font-semibold">SEO-пакеты по платформам</h2><div className="mt-4 grid gap-4">{[['youtubeVideo', 'YouTube Video'], ['youtubeShorts', 'YouTube Shorts'], ['instagramReels', 'Instagram Reels'], ['tiktok', 'TikTok']].map(([key, title]) => {const data = seoDraft[key as string] || {}; const packageText = [`Платформа: ${title}`, `Главный заголовок: ${data.bestTitle || data.caption || ''}`, `Варианты заголовков: ${(data.titleOptions || []).join(' | ')}`, `Описание: ${data.description || data.caption || ''}`, `Хештеги: ${(data.hashtags || []).join(' ')}`, `Теги: ${(data.tags || []).join(', ')}`, `Текст обложки: ${data.coverText || data.thumbnailText || ''}`, `Закреплённый комментарий: ${data.pinnedComment || ''}`, `Рекомендации: ${(data.improvementTips || []).join(' | ')}`].join('\n\n'); return (<section key={key} className="rounded-xl border border-slate-200 p-4"><div className="flex items-center justify-between"><h3 className="text-base font-semibold">{title}</h3><CopyButton text={packageText} /></div><div className="mt-3 grid gap-3 text-sm"><MetricCard label="Главный заголовок / caption" value={data.bestTitle || data.caption || '—'} /><MetricCard label="Варианты заголовков" value={(data.titleOptions || []).join(' • ') || '—'} /><MetricCard label="Описание" value={data.description || data.caption || '—'} /><MetricCard label="Хештеги" value={(data.hashtags || []).join(' ') || '—'} /><MetricCard label="Теги" value={(data.tags || []).join(', ') || '—'} /><MetricCard label="Текст обложки" value={data.coverText || data.thumbnailText || '—'} /><MetricCard label="Закреплённый комментарий" value={data.pinnedComment || '—'} /><MetricCard label="Рекомендации" value={(data.improvementTips || []).join(' • ') || '—'} /></div></section>);})}</div></article>

            <details className={cardClass}><summary className="cursor-pointer text-sm font-medium">Показать технический JSON</summary><pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(job, null, 2)}</pre></details>
          </section>
        )}
      </div>
    </main>
  );
}
