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

const contextLabels: Record<string, string> = {
  views_and_reach: 'Охваты и просмотры',
  subscribers: 'Подписчики',
  leads: 'Заявки / клиенты',
  portfolio: 'Портфолио',
  sales: 'Продажи',
  auto: 'Авто',
  real_estate: 'Недвижимость',
  travel: 'Путешествия',
  expert_content: 'Экспертный контент',
  music_event: 'Музыка / мероприятия',
  beauty: 'Beauty',
  food: 'Еда',
  education: 'Образование',
  general_video: 'Общее видео',
  travel_destination_short: 'Travel / направление',
  travel_resort_reels: 'Travel / курорт',
  travel_horizontal_story: 'Travel / YouTube story',
  urban_drive: 'Городская поездка',
  urban_drive_sunset: 'Городская поездка на закате',
  urban_drive_cinematic: 'Атмосферная городская поездка',
  auto_cinematic: 'Автомобильный синематик',
  auto_detail_showcase: 'Детальный показ автомобиля',
  auto_review: 'Автомобильный обзор',
  auto_sale: 'Автомобиль для продажи',
  event_people_scene: 'Событие с людьми',
  event_scene: 'Событие',
  talking_head: 'Разговорное видео',
  product_showcase: 'Демонстрация продукта',
  tutorial: 'Обучающее видео',
  story_reveal: 'История с раскрытием',
  ambient_scene: 'Атмосферная сцена',
  generic_video: 'Общее видео',
  ru: 'Русский',
  en: 'Английский'
};

const cardClass = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm';

const platformMeta: Record<string, { title: string; hint: string }> = {
  youtubeVideo: {
    title: 'YouTube Video',
    hint: 'Для длинного или горизонтального формата'
  },
  youtubeShorts: {
    title: 'Shorts',
    hint: 'Короткий вертикальный формат'
  },
  instagramReels: {
    title: 'Reels',
    hint: 'Визуальный caption и эстетика'
  },
  tiktok: {
    title: 'TikTok',
    hint: 'Короткий hook и трендовая подача'
  }
};

type PlatformField = {
  label: string;
  value: (data: any) => any;
  kind?: 'chips' | 'text';
};

const fieldOrder: Record<string, PlatformField[]> = {
  youtubeVideo: [
    { label: 'Главный заголовок', value: (d) => d.bestTitle || d.caption },
    { label: 'Варианты заголовков', value: (d) => d.titleOptions },
    { label: 'Описание', value: (d) => d.description || d.caption, kind: 'text' },
    { label: 'Tags', value: (d) => d.tags, kind: 'chips' },
    { label: 'Thumbnail text', value: (d) => d.thumbnailText || d.coverText },
    { label: 'Pinned comment', value: (d) => d.pinnedComment, kind: 'text' },
    { label: 'CTA', value: (d) => d.cta },
    { label: 'Рекомендации', value: (d) => d.improvementTips }
  ],
  youtubeShorts: [
    { label: 'Hook text', value: (d) => d.hookText || d.firstLineHook },
    { label: 'Главный заголовок', value: (d) => d.bestTitle || d.caption },
    { label: 'Описание', value: (d) => d.description || d.caption, kind: 'text' },
    { label: 'Hashtags', value: (d) => d.hashtags, kind: 'chips' },
    { label: 'Cover text', value: (d) => d.coverText || d.thumbnailText },
    { label: 'Pinned comment', value: (d) => d.pinnedComment, kind: 'text' },
    { label: 'Рекомендации', value: (d) => d.improvementTips }
  ],
  instagramReels: [
    { label: 'First line hook', value: (d) => d.firstLineHook || d.hookText },
    { label: 'Caption', value: (d) => d.caption || d.description, kind: 'text' },
    { label: 'Hashtags', value: (d) => d.hashtags, kind: 'chips' },
    { label: 'Cover text', value: (d) => d.coverText },
    { label: 'Alt text', value: (d) => d.altText, kind: 'text' },
    { label: 'Story announcement', value: (d) => d.storyAnnouncement, kind: 'text' },
    { label: 'CTA', value: (d) => d.cta },
    { label: 'Pinned comment', value: (d) => d.pinnedComment, kind: 'text' },
    { label: 'Рекомендации', value: (d) => d.improvementTips }
  ],
  tiktok: [
    { label: 'Hook text', value: (d) => d.hookText || d.firstLineHook },
    { label: 'Caption', value: (d) => d.caption || d.description, kind: 'text' },
    { label: 'Trend angle', value: (d) => d.trendAngle },
    { label: 'Hashtags', value: (d) => d.hashtags, kind: 'chips' },
    { label: 'Cover text', value: (d) => d.coverText || d.thumbnailText },
    { label: 'CTA', value: (d) => d.cta },
    { label: 'Pinned comment', value: (d) => d.pinnedComment, kind: 'text' },
    { label: 'Рекомендации', value: (d) => d.improvementTips }
  ]
};

const isEmpty = (value: any) =>
  value == null || value === '' || value === '—' || (Array.isArray(value) && value.length === 0);

const readable = (value: string) => contextLabels[value] || value;

const getPlatformScore = (platformKey: string, platformFit: any) => {
  return platformFit?.[platformKey]?.score ?? -1;
};

const normalizeCopyValue = (value: any) => {
  if (isEmpty(value)) return '';
  if (Array.isArray(value)) return value.map((item) => String(item)).join('\n');
  return String(value);
};

const formatFieldValue = (value: any, label: string) => {
  if (Array.isArray(value)) {
    if (label === 'Hashtags') {
      return value.map((item) => {
        const text = String(item);
        return text.startsWith('#') ? text : `#${text}`;
      });
    }

    return value.map((item) => String(item));
  }

  return value;
};

const getBestPlatform = (platformFit: any, videoFingerprint: any) => {
  const entries = [
    { key: 'youtubeVideo', score: getPlatformScore('youtubeVideo', platformFit) },
    { key: 'youtubeShorts', score: getPlatformScore('youtubeShorts', platformFit) },
    { key: 'instagramReels', score: getPlatformScore('instagramReels', platformFit) },
    { key: 'tiktok', score: getPlatformScore('tiktok', platformFit) }
  ];

  const maxScore = Math.max(...entries.map((item) => item.score));
  const winners = entries.filter((item) => item.score === maxScore).map((item) => item.key);

  if (winners.length === 1) return winners[0];

  const isHorizontal = String(videoFingerprint?.orientation || '').toLowerCase().includes('horiz');
  if (isHorizontal && winners.includes('youtubeVideo')) return 'youtubeVideo';
  if (winners.includes('youtubeShorts')) return 'youtubeShorts';
  if (winners.includes('youtubeVideo')) return 'youtubeVideo';
  return winners[0] || 'youtubeShorts';
};

function CopyButton({ text, label = 'Скопировать' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  const handleCopy = async () => {
    if (!text) return;

    try {
      if (!navigator?.clipboard?.writeText) {
        setFailed(true);
        setTimeout(() => setFailed(false), 1500);
        return;
      }

      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setFailed(true);
      setTimeout(() => setFailed(false), 1500);
    }
  };

  return (
    <button
      onClick={handleCopy}
      disabled={!text}
      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {copied ? 'Скопировано' : failed ? 'Ошибка' : label}
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

const formatSeconds = (value: any) => {
  if (value == null || value === '') return '—';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(numeric < 10 ? 1 : 0)} сек` : '—';
};

const confidenceLabel = (value: any) => {
  if (value == null || value === '') return '—';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${Math.round(numeric * 100)}%` : '—';
};

function InsightList({ items, empty = 'Нет данных' }: { items?: any[]; empty?: string }) {
  const values = Array.isArray(items) ? items.filter(Boolean).map(String) : [];
  if (values.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
      {values.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
    </ul>
  );
}

function FullVideoIntelligenceCard({
  intelligence,
  opening,
  temporal,
  audio,
  transcript,
  retention
}: {
  intelligence: any;
  opening: any;
  temporal: any;
  audio: any;
  transcript: any;
  retention: any;
}) {
  const openingHook = intelligence?.openingHook || opening || {};
  const editing = intelligence?.editing || temporal || {};
  const audioSummary = intelligence?.audio || {};
  const hasAudio = audio?.hasAudio ?? audioSummary?.hasAudio;
  const hasSpeech = audioSummary?.speechPresent ?? audio?.speechPresent;
  const story = intelligence?.story || {};
  const retentionSummary = retention || intelligence?.retention || {};
  const hasPipelineData = Boolean(intelligence || opening || temporal || audio || transcript);

  if (!hasPipelineData) return null;

  return (
    <article className={cardClass}>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Video Intelligence</p>
        <h2 className="mt-1 text-xl font-semibold">Полный анализ видео</h2>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Обзор</h3>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p>{intelligence?.summary || 'Единый AI-обзор недоступен; показаны доступные этапы анализа.'}</p>
            <p><span className="font-medium">Формат:</span> {intelligence?.contentType || '—'}</p>
            <p><span className="font-medium">Основная тема:</span> {intelligence?.primarySubject || '—'}</p>
            <p><span className="font-medium">Уверенность:</span> {confidenceLabel(intelligence?.confidence)}</p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Первые 3 секунды</h3>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p>{openingHook?.summary || openingHook?.visualSummary || '—'}</p>
            <p><span className="font-medium">Тип hook:</span> {openingHook?.type || openingHook?.hookType || '—'}</p>
            <p><span className="font-medium">Сила:</span> {confidenceLabel(openingHook?.strength ?? openingHook?.hookStrength)}</p>
            <p><span className="font-medium">Риск удержания:</span> {openingHook?.retentionRisk || '—'}</p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Монтаж</h3>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <MetricCard label="Сцен" value={String(editing?.estimatedSceneCount ?? '—')} />
            <MetricCard label="Темп" value={String(editing?.pacing || '—')} />
            <MetricCard label="Смен в минуту" value={String(editing?.cutsPerMinute ?? '—')} />
            <MetricCard label="Средняя сцена" value={formatSeconds(editing?.averageShotDurationSec)} />
          </div>
          {(editing?.strengths?.length > 0 || editing?.weaknesses?.length > 0) && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div><p className="mb-1 text-xs font-semibold text-slate-500">Сильные стороны</p><InsightList items={editing.strengths} /></div>
              <div><p className="mb-1 text-xs font-semibold text-slate-500">Что мешает</p><InsightList items={editing.weaknesses} /></div>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Аудио и речь</h3>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p><span className="font-medium">Аудио:</span> {hasAudio == null ? '—' : hasAudio ? 'есть' : 'не обнаружено'}</p>
            <p><span className="font-medium">Речь:</span> {hasSpeech == null ? '—' : hasSpeech ? 'обнаружена' : 'не подтверждена'}</p>
            <p>{audioSummary?.speechSummary || 'Краткое содержание речи недоступно.'}</p>
            <p className="text-xs text-slate-500">Статус транскрипции: {transcript?.status || audio?.transcriptionStatus || '—'}</p>
            {transcript?.text && (
              <details className="rounded-lg bg-slate-50 p-3">
                <summary className="cursor-pointer font-medium">Показать транскрипт</summary>
                <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed">{transcript.text}</p>
              </details>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Сюжет</h3>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <p><span className="font-medium">Структура:</span> {story?.structure || '—'}</p>
            <p><span className="font-medium">Начало:</span> {story?.beginning || '—'}</p>
            <p><span className="font-medium">Развитие:</span> {story?.development || '—'}</p>
            <p><span className="font-medium">Payoff / финал:</span> {story?.payoff || story?.ending || '—'}</p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <h3 className="font-semibold">Удержание</h3>
          <p className="mt-1 text-xs text-slate-500">{retentionSummary?.disclaimer || 'Экспертная оценка, не фактическая аналитика удержания.'}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div><p className="mb-1 text-xs font-semibold text-slate-500">Сильные стороны</p><InsightList items={retentionSummary?.strengths} /></div>
            <div><p className="mb-1 text-xs font-semibold text-slate-500">Риски</p><InsightList items={retentionSummary?.risks} /></div>
          </div>
          <div className="mt-3"><p className="mb-1 text-xs font-semibold text-slate-500">Что улучшить</p><InsightList items={retentionSummary?.recommendedEdits || retentionSummary?.improvements} /></div>
        </section>
      </div>

      <section className="mt-4 rounded-xl border border-slate-200 p-4">
        <h3 className="font-semibold">Лучшие моменты</h3>
        {intelligence?.strongestMoments?.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {intelligence.strongestMoments.map((moment: any, index: number) => (
              <div key={`${moment.timestampSec}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <span className="font-semibold text-blue-700">{formatSeconds(moment.timestampSec)}</span>
                <span className="ml-2 text-slate-700">{moment.reason || 'Сильный момент ролика'}</span>
              </div>
            ))}
          </div>
        ) : <p className="mt-2 text-sm text-slate-500">Не определены.</p>}
      </section>
    </article>
  );
}

function SeoPlatformCard({
  title,
  data,
  platformKey,
  score
}: {
  title: string;
  data: any;
  platformKey: string;
  score?: number;
}) {
  const rows = (fieldOrder[platformKey] || [])
    .map((field) => ({ ...field, valueRaw: field.value(data) }))
    .filter((field) => !isEmpty(field.valueRaw));

  const packageText = rows
    .map((row) => `${row.label}: ${normalizeCopyValue(formatFieldValue(row.valueRaw, row.label))}`)
    .join('\n\n');

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-2xl font-bold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm text-slate-500">{platformMeta[platformKey]?.hint}</p>
        </div>

        <div className="flex items-center gap-2">
          {Number.isFinite(score) && (
            <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">Score: {score}</span>
          )}
          <CopyButton text={packageText} label="Скопировать пакет" />
        </div>
      </div>

      <div className="space-y-3">
        {rows.map((row) => {
          const formatted = formatFieldValue(row.valueRaw, row.label);
          const fieldText = normalizeCopyValue(formatted);
          const useChips = row.kind === 'chips' && Array.isArray(formatted);
          const useList = Array.isArray(formatted) && !useChips;

          return (
            <div key={row.label} className="rounded-xl border border-slate-200 p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-700">{row.label}</p>
                <CopyButton text={fieldText} />
              </div>

              {useChips && (
                <div className="flex flex-wrap gap-2">
                  {formatted.map((item: string, index: number) => {
                    const chipText = row.label === 'Tags' ? item : item.startsWith('#') ? item : `#${item}`;
                    return (
                      <span
                        key={`${row.label}-${index}`}
                        className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700"
                      >
                        {chipText}
                      </span>
                    );
                  })}
                </div>
              )}

              {useList && (
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-900">
                  {formatted.map((item: string, index: number) => (
                    <li key={`${row.label}-item-${index}`}>{item}</li>
                  ))}
                </ul>
              )}

              {!Array.isArray(formatted) && (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-900">{formatted}</p>
              )}
            </div>
          );
        })}
      </div>
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
  const [activePlatform, setActivePlatform] = useState('youtubeShorts');
  const [lastAutoSelectedJobId, setLastAutoSelectedJobId] = useState<string | null>(null);

  const [contextForm, setContextForm] = useState({
    userGoal: 'views_and_reach',
    niche: 'general_video',
    language: 'ru',
    geo: '',
    brandName: '',
    keywords: ''
  });

  const upload = async () => {
    if (!file || isUploading) return;

    setIsUploading(true);
    setError(null);
    setJob(null);
    setLastAutoSelectedJobId(null);

    const form = new FormData();
    form.append('video', file);
    Object.entries(contextForm).forEach(([key, value]) => form.append(key, value));

    try {
      const response = await fetch(`${API_URL}/api/videos/upload`, {
        method: 'POST',
        body: form
      });
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
      if (!response.ok) {
        setError(data.error || 'Не удалось получить статус задачи');
      }
    } catch {
      setError('Ошибка сети при получении статуса');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (jobId) refresh(jobId);
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !job || job.status === 'done' || job.status === 'failed') return;
    const intervalId = setInterval(() => refresh(jobId), 2500);
    return () => clearInterval(intervalId);
  }, [jobId, job?.status]);

  const report = job?.analysis_report;
  const seoDraft = report?.seoDraft || {};
  const platformFit = report?.platformFit || {};
  const aiInput = report?.ai_input || {};
  const visualAnalysis = aiInput?.visualAnalysis || null;
  const videoIntelligence = report?.videoIntelligence || aiInput?.videoIntelligence || null;
  const openingAnalysis = report?.openingAnalysis || aiInput?.openingAnalysis || null;
  const temporalAnalysis = report?.temporalAnalysis || aiInput?.temporalAnalysis || null;
  const audioAnalysis = report?.audioAnalysis || aiInput?.audioAnalysis || null;
  const transcript = report?.transcript || aiInput?.transcript || null;
  const retentionAnalysis = report?.retentionAnalysis || aiInput?.retentionAnalysis || null;
  const videoFingerprint = aiInput?.videoFingerprint || {};
  const statusText = useMemo(
    () => (job?.status ? statusLabels[job.status] || job.status : null),
    [job?.status]
  );

  const fallbackContext = job?.user_context || {};
  const contextSource = {
    ...fallbackContext,
    ...aiInput,
    brandName: aiInput?.brandName || fallbackContext?.brandName || '',
    keywords:
      Array.isArray(aiInput?.keywords) && aiInput.keywords.length > 0
        ? aiInput.keywords
        : fallbackContext?.keywords || []
  };

  useEffect(() => {
    const resolvedJobId = String(job?.id || jobId || '');
    if (!resolvedJobId || job?.status !== 'done' || lastAutoSelectedJobId === resolvedJobId) return;

    const bestPlatform = getBestPlatform(platformFit, videoFingerprint);
    setActivePlatform(bestPlatform);
    setLastAutoSelectedJobId(resolvedJobId);
  }, [job?.id, job?.status, jobId, lastAutoSelectedJobId, platformFit, videoFingerprint]);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="flex items-start justify-between">
          <div>
            <p className="text-2xl font-bold tracking-tight">SEO-GURU</p>
            <p className="mt-1 text-sm text-slate-600">AI-анализ видео и SEO для YouTube, Shorts, Reels и TikTok</p>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">MVP / Local demo</span>
        </header>

        <section className={cardClass}>
          <h2 className="text-lg font-semibold">Настройки анализа</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Цель публикации</span>
              <select className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2" value={contextForm.userGoal} onChange={(e) => setContextForm((prev) => ({ ...prev, userGoal: e.target.value }))}>{goalOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Ниша</span>
              <select className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2" value={contextForm.niche} onChange={(e) => setContextForm((prev) => ({ ...prev, niche: e.target.value }))}>{nicheOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Язык</span>
              <select className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2" value={contextForm.language} onChange={(e) => setContextForm((prev) => ({ ...prev, language: e.target.value }))}>{languageOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Видео файл</span>
              <input type="file" accept="video/*" className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </label>
          </div>
          <button onClick={upload} disabled={!file || isUploading} className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white disabled:bg-blue-300">{isUploading ? 'Загрузка…' : 'Проанализировать видео'}</button>
        </section>

        {jobId && (
          <section className={cardClass}>
            <p className="text-xs text-slate-500">Job ID: {jobId}</p>
            <p className="mt-1 text-sm">Статус: <span className="font-semibold">{statusText || '—'}</span></p>
            <button onClick={() => refresh()} disabled={!jobId || isRefreshing} className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm">{isRefreshing ? 'Обновление…' : 'Обновить статус'}</button>
          </section>
        )}

        {job && report && (
          <section className="grid gap-4">
            <article className={cardClass}>
              <h2 className="text-lg font-semibold">Контекст анализа</h2>
              <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                <MetricCard label="Цель" value={readable(contextSource.userGoal) || 'Не указано'} />
                <MetricCard label="Ниша" value={readable(contextSource.niche) || 'Не указано'} />
                <MetricCard label="Язык" value={readable(contextSource.language) || 'Не указано'} />
              </div>
            </article>

            <FullVideoIntelligenceCard
              intelligence={videoIntelligence}
              opening={openingAnalysis}
              temporal={temporalAnalysis}
              audio={audioAnalysis}
              transcript={transcript}
              retention={retentionAnalysis}
            />

            <article className={cardClass}>
              <h2 className="text-lg font-semibold">Видео-подсказки</h2>
              <div className="mt-3 space-y-2">
                <p className="text-xl font-semibold">{videoFingerprint.orientation?.includes('horiz') ? 'Горизонтальный формат' : 'Вертикальный короткий ролик'}</p>
                <p className="text-base">{readable(aiInput?.videoAngle || '') || 'Не определено'}</p>
                <p className="text-xs text-slate-500">(technical: {aiInput?.videoAngle || 'n/a'}, basis: {(aiInput?.generationBasis || []).join(', ') || 'n/a'})</p>
                <div className="flex flex-wrap gap-2">{(aiInput?.contentHints || []).map((hint: string) => <span key={hint} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">{hint}</span>)}</div>
              </div>
            </article>
            <article className={cardClass}>
              <h2 className="text-lg font-semibold">AI-визуальный анализ</h2>
              {!visualAnalysis ? (
                <p className="mt-3 text-sm text-slate-500">
                  AI-визуальный анализ недоступен. Используется fallback по техническим данным и контексту.
                </p>
              ) : (
                <div className="mt-3 space-y-3 text-sm">
                  <p><span className="font-semibold">Краткое описание:</span> {visualAnalysis.summary || '—'}</p>
                  <p><span className="font-semibold">Сцена:</span> {visualAnalysis.detectedScene || '—'}</p>
                  <p><span className="font-semibold">Тип локации:</span> {visualAnalysis.detectedLocationType || '—'}</p>
                  <p><span className="font-semibold">Предложенная ниша:</span> {visualAnalysis.suggestedNiche || '—'}</p>
                  <p><span className="font-semibold">Предложенный угол:</span> {visualAnalysis.suggestedVideoAngle || '—'}</p>
                  <p><span className="font-semibold">Уверенность:</span> {visualAnalysis.confidence ?? '—'}</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="w-full text-xs font-semibold text-slate-600">Объекты</span>
                    {(visualAnalysis.detectedObjects || []).map((x: string, i: number) => <span key={`obj-${i}`} className="rounded-full bg-slate-100 px-2 py-1 text-xs">{x}</span>)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="w-full text-xs font-semibold text-slate-600">Стиль</span>
                    {(visualAnalysis.style || []).map((x: string, i: number) => <span key={`style-${i}`} className="rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800">{x}</span>)}
                    <span className="w-full text-xs font-semibold text-slate-600">Настроение</span>
                    {(visualAnalysis.mood || []).map((x: string, i: number) => <span key={`mood-${i}`} className="rounded-full bg-emerald-100 px-2 py-1 text-xs text-emerald-800">{x}</span>)}
                  </div>
                  <p className="text-xs font-semibold text-slate-600">Лучшие кадры</p>
                  <ul className="list-disc pl-5">
                    {(visualAnalysis.bestFrames || []).map((f: any, i: number) => <li key={`best-${i}`}>Frame {f.frameIndex} · {formatSeconds(f.timestampSec)}: {f.reason}</li>)}
                  </ul>
                </div>
              )}
            </article>

            <article className={cardClass}>
              <h2 className="text-lg font-semibold">SEO-пакеты по платформам</h2>
              <div className="mt-4 overflow-x-auto">
                <div className="flex min-w-max gap-2">
                  {Object.entries(platformMeta).map(([key, meta]) => (
                    <button key={key} onClick={() => setActivePlatform(key)} className={`rounded-full px-4 py-2 text-sm ${activePlatform === key ? 'bg-slate-900 text-white' : 'border border-slate-300 bg-white text-slate-700'}`}>
                      <span>{meta.title}</span>
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-[10px] ${activePlatform === key ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'}`}>{getPlatformScore(key, platformFit)}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4">
                {Object.entries(platformMeta).map(([key, meta]) => (
                  activePlatform === key ? <SeoPlatformCard key={key} title={meta.title} platformKey={key} data={seoDraft[key] || {}} score={getPlatformScore(key, platformFit)} /> : null
                ))}
              </div>
            </article>

            <details className={cardClass}>
              <summary className="cursor-pointer text-sm font-medium">Показать технический JSON</summary>
              <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(job, null, 2)}</pre>
            </details>
          </section>
        )}
      </div>
    </main>
  );
}
