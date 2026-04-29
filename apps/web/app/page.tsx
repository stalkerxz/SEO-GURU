'use client';
import { useEffect, useMemo, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';
const goals = ['views_and_reach', 'subscribers', 'leads', 'portfolio', 'sales'];
const niches = ['auto', 'real_estate', 'travel', 'expert_content', 'music_event', 'beauty', 'food', 'education', 'general_video'];
const languages = ['ru', 'en'];

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ userGoal: 'views_and_reach', niche: 'general_video', language: 'ru', geo: '', brandName: '', keywords: '' });

  const upload = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append('video', file);
    Object.entries(form).forEach(([k, v]) => fd.append(k, v));
    const response = await fetch(`${API_URL}/api/videos/upload`, { method: 'POST', body: fd });
    const data = await response.json();
    if (!response.ok) return setError(data.error || 'Не удалось загрузить видео');
    setError(null); setJob(null); setJobId(data.jobId);
  };
  const refresh = async (id?: string) => { const x = id || jobId; if (!x) return; const r = await fetch(`${API_URL}/api/jobs/${x}`); const d = await r.json(); setJob(d); if (!r.ok) setError(d.error); };
  useEffect(() => { if (jobId) refresh(jobId); }, [jobId]);
  useEffect(() => { if (!jobId || !job || ['done', 'failed'].includes(job.status)) return; const id = setInterval(() => refresh(jobId), 2000); return () => clearInterval(id); }, [jobId, job?.status]);

  const report = job?.analysis_report;
  const aiInput = report?.ai_input || {};
  const seoDraft = report?.seoDraft || {};
  const statusText = useMemo(() => {
    const labels: Record<string, string> = { queued: 'Видео в очереди', processing: 'Идёт анализ видео', done: 'Анализ готов', failed: 'Ошибка анализа' };
    return labels[job?.status as string] || job?.status;
  }, [job?.status]);

  const copyPackage = async (data: any) => {
    const text = [data.bestTitle || data.caption, data.description || data.caption, `Hashtags: ${(data.hashtags || []).join(' ')}`, data.tags ? `Tags: ${data.tags.join(', ')}` : '', `Pinned: ${data.pinnedComment || ''}`, `Cover: ${data.coverText || data.thumbnailText || ''}`].filter(Boolean).join('\n\n');
    await navigator.clipboard.writeText(text);
  };

  return <main className="max-w-5xl mx-auto p-6 space-y-4"><h1 className="text-2xl font-bold">Video SEO Analyzer</h1>
    <div className="grid md:grid-cols-2 gap-3 border p-3 rounded">
      <select value={form.userGoal} onChange={(e)=>setForm({...form,userGoal:e.target.value})}>{goals.map(v=><option key={v}>{v}</option>)}</select>
      <select value={form.niche} onChange={(e)=>setForm({...form,niche:e.target.value})}>{niches.map(v=><option key={v}>{v}</option>)}</select>
      <select value={form.language} onChange={(e)=>setForm({...form,language:e.target.value})}>{languages.map(v=><option key={v}>{v}</option>)}</select>
      <input placeholder="Гео" value={form.geo} onChange={(e)=>setForm({...form,geo:e.target.value})} className="border p-2 rounded"/>
      <input placeholder="Бренд/автор" value={form.brandName} onChange={(e)=>setForm({...form,brandName:e.target.value})} className="border p-2 rounded"/>
      <input placeholder="Ключевые слова" value={form.keywords} onChange={(e)=>setForm({...form,keywords:e.target.value})} className="border p-2 rounded md:col-span-2"/>
    </div>
    <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
    <div className="flex gap-2"><button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={upload}>Upload</button><button className="bg-slate-700 text-white px-4 py-2 rounded" onClick={() => refresh()} disabled={!jobId}>Refresh status</button></div>
    {jobId && <p>Job ID: {jobId}</p>}{error && <p className="text-red-600">{error}</p>}
    {job && <div className="bg-white rounded p-4 shadow space-y-4"><p><b>{statusText}</b></p>
      <section><h2 className="font-semibold">Контекст анализа</h2><ul className="list-disc ml-5 text-sm"><li>Цель: {aiInput.userGoal || '—'}</li><li>Ниша: {aiInput.niche || '—'}</li><li>Язык: {aiInput.language || '—'}</li><li>Гео: {aiInput.geo || '—'}</li><li>Бренд: {aiInput.brandName || '—'}</li><li>Ключевые слова: {(aiInput.keywords || []).join(', ') || '—'}</li></ul></section>
      {['youtubeVideo','youtubeShorts','instagramReels','tiktok'].map((k)=>{const d:any=seoDraft[k]||{}; return <div key={k} className="border rounded p-3 space-y-1"><h3 className="font-semibold">{k}</h3><button className="text-xs bg-black text-white px-2 py-1 rounded" onClick={()=>copyPackage(d)}>Скопировать весь SEO-пакет</button><p>{d.bestTitle || d.caption}</p><p className="text-sm">{d.description || d.caption}</p><p className="text-sm">{(d.hashtags||[]).join(' ')}</p></div>})}
    </div>}
  </main>;
}
