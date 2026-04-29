'use client';
import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<any>(null);

  const upload = async () => {
    if (!file) return;
    const form = new FormData();
    form.append('video', file);
    const response = await fetch(`${API_URL}/api/videos/upload`, { method: 'POST', body: form });
    const data = await response.json();
    setJobId(data.jobId);
  };

  const refresh = async () => {
    if (!jobId) return;
    const response = await fetch(`${API_URL}/api/jobs/${jobId}`);
    setJob(await response.json());
  };

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Video SEO Analyzer</h1>
      <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <div className="flex gap-2">
        <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={upload}>Upload</button>
        <button className="bg-slate-700 text-white px-4 py-2 rounded" onClick={refresh} disabled={!jobId}>Refresh status</button>
      </div>

      {jobId && <p>Job ID: {jobId}</p>}
      {job && (
        <div className="bg-white rounded p-4 shadow space-y-2">
          <p><b>Status:</b> {job.status}</p>
          <p><b>Technical params:</b> {JSON.stringify(job.result)}</p>
          <p><b>Frames:</b> {JSON.stringify(job.frames)}</p>
          <pre className="bg-slate-900 text-green-300 p-3 rounded overflow-auto text-xs">{JSON.stringify(job, null, 2)}</pre>
        </div>
      )}
    </main>
  );
}
