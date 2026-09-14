"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

function confidenceClass(score) {
  if (score >= 0.8) return "bg-emerald-100 text-emerald-800";
  if (score >= 0.65) return "bg-amber-100 text-amber-800";
  return "bg-rose-100 text-rose-800";
}

function filenameOnly(path) {
  try {
    if (!path) return "";
    const parts = path.split(/[\\/]/);
    return parts[parts.length - 1];
  } catch {
    return path;
  }
}

export default function MappingReviewPage() {
  const { jobId } = useParams();
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  const [meta, setMeta] = useState({ source_file: "", target_file: "" });
  const [suggestions, setSuggestions] = useState([]);
  const [approved, setApproved] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState("");
  const [onlyUnmapped, setOnlyUnmapped] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const sRes = await fetch(`${base}/mapping/jobs/${encodeURIComponent(jobId)}`);
        if (!sRes.ok) throw new Error(`HTTP ${sRes.status}`);
        const sData = await sRes.json();

        const aRes = await fetch(`${base}/mapping/jobs/${encodeURIComponent(jobId)}/approved`);
        const aData = aRes.ok ? await aRes.json() : null;

        if (!mounted) return;
        setMeta({ source_file: sData.source_file || "", target_file: sData.target_file || "" });
        setSuggestions(sData.suggestions || []);

        const initial = { ...(aData?.approved_mapping || {}) };
        for (const s of sData.suggestions || []) {
          if (!(s.source_column in initial)) {
            initial[s.source_column] = s.best_target && s.best_target !== "UNMAPPED" ? s.best_target : null;
          }
        }
        setApproved(initial);
      } catch (e) {
        setError(e.message || String(e));
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [base, jobId]);

  const visible = useMemo(() => {
    const t = filter.trim().toLowerCase();
    return suggestions.filter((s) => {
      if (!s) return false;
      if (t && !s.source_column.toLowerCase().includes(t)) return false;
      if (onlyUnmapped) {
        const val = approved[s.source_column];
        if (val !== null && val !== undefined) return false;
      }
      return true;
    });
  }, [suggestions, filter, onlyUnmapped, approved]);

  const approvedCount = Object.values(approved).filter((v) => v !== null).length;
  const total = suggestions.length || 0;

  async function save() {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${base}/mapping/jobs/${encodeURIComponent(jobId)}/approved`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_mapping: approved }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6">
      <div className="sticky top-4 z-30 bg-white/90 backdrop-blur-sm border rounded-md p-4 mb-4 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-lg font-semibold truncate">Validate Mapping</div>
          <div className="text-sm text-slate-500 truncate">{jobId}</div>
        </div>

        <div className="hidden md:block text-slate-600 truncate max-w-[40%] text-center">
          {filenameOnly(meta.source_file)} {" → "} {filenameOnly(meta.target_file)}
        </div>

        <div className="flex items-center gap-3">
          <div className="text-sm text-slate-600">{approvedCount}/{total} approved</div>
          <button
            onClick={save}
            disabled={saving}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              saving ? "bg-slate-300 text-slate-700 cursor-not-allowed" : "bg-slate-900 text-white hover:bg-slate-800"
            }`}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <div className="sticky top-20 z-20 bg-white/90 backdrop-blur-sm border rounded-md p-3 mb-4 flex flex-col md:flex-row items-start md:items-center gap-3">
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter source columns…"
          className="w-full md:w-1/2 rounded-md border px-3 py-2 bg-white text-sm"
        />
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={onlyUnmapped}
            onChange={(e) => setOnlyUnmapped(e.target.checked)}
            className="h-4 w-4"
          />
          Show only unmapped
        </label>
        <div className="ml-auto text-sm text-slate-600 hidden md:block">{loading ? "Loading…" : error ? "" : `${approvedCount} of ${total} approved`}</div>
      </div>

      {error ? (
        <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 rounded mb-4">
          <div className="font-medium">Could not load mapping suggestions</div>
          <div className="mt-1 text-sm">{error}</div>
          <div className="mt-1 text-xs text-slate-500">Base: {base}</div>
        </div>
      ) : loading ? (
        <div className="p-6 bg-white border rounded-lg text-slate-600">Loading suggestions…</div>
      ) : (
        <div className="grid gap-4">
          {visible.map((s) => {
            const options = ["UNMAPPED", ...(s.candidates || []).map((c) => c.target_column)];
            const current = approved[s.source_column] ?? null;
            return (
              <div key={s.source_column} className="bg-white border rounded-lg p-4 shadow-sm hover:shadow-md transition">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900 truncate max-w-xl">{s.source_column}</div>
                    <div className="text-sm text-slate-600 mt-1 flex items-center gap-3">
                      <span className="text-xs text-slate-500">Best:</span>
                      <span className="text-sm truncate max-w-[60%]">{s.best_target ?? "UNMAPPED"}</span>
                      <span className={`ml-2 inline-flex items-center px-2 py-0.5 text-xs rounded ${confidenceClass(s.best_confidence ?? 0)}`}>{(s.best_confidence ?? 0).toFixed(3)}</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-3">
                    <select
                      value={current === null ? "UNMAPPED" : current}
                      onChange={(e) => {
                        const v = e.target.value === "UNMAPPED" ? null : e.target.value;
                        setApproved((p) => ({ ...p, [s.source_column]: v }));
                      }}
                      className="rounded-md border px-3 py-2 bg-white"
                    >
                      {options.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="text-left text-slate-600">
                        <th className="pb-2">Candidate</th>
                        <th className="pb-2 text-right">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(s.candidates || []).map((c, idx) => (
                        <tr key={c.target_column} className={idx % 2 === 0 ? "bg-slate-50" : ""}>
                          <td className="py-2 pr-4">{c.target_column}</td>
                          <td className="py-2 text-right">{Number(c.confidence).toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
