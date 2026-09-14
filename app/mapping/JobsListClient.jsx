"use client";

import { useMemo, useState } from "react";

export default function JobsListClient({ jobs = [] }) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return jobs;
    return jobs.filter((j) => j.job_id.toLowerCase().includes(term));
  }, [jobs, q]);

  return (
    <div>
      <div className="mb-4 flex gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search jobs…"
          className="w-full rounded-md border px-3 py-2 bg-white"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {filtered.map((j) => (
          <a
            key={j.job_id}
            href={`/mapping/${encodeURIComponent(j.job_id)}`}
            className="block p-4 bg-white border rounded-lg hover:shadow"
          >
            <div className="font-medium">{j.job_id}</div>
            <div className="text-sm text-slate-500 mt-1">{j.source_file || "source"} → {j.target_file || "target"}</div>
          </a>
        ))}
      </div>
    </div>
  );
}
