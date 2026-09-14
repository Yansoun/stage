import JobsListClient from "./JobsListClient";

export default async function MappingJobsPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

  let jobs = [];
  let error = "";

  try {
    const res = await fetch(`${base}/mapping/jobs`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    jobs = await res.json();
  } catch (e) {
    error = e.message || String(e);
  }

  return (
    <section className="max-w-6xl mx-auto px-6">
      <div className="flex items-start justify-between gap-6 mb-6">
        <div>
          <h1 className="text-3xl font-semibold">Mapping Jobs</h1>
          <p className="mt-1 text-slate-600">Review AI mapping suggestions and approve mappings</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-sm text-slate-500">Total:</div>
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-slate-100 text-slate-800 font-medium">
            {jobs.length}
          </div>
        </div>
      </div>

      {error ? (
        <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 rounded">
          <div className="font-medium">Could not load jobs</div>
          <div className="mt-1 text-sm">Base: {base}</div>
          <div className="mt-1 text-sm">{error}</div>
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-6 bg-white border rounded-lg shadow-sm">
          <div className="text-lg font-medium">No mapping jobs found</div>
          <p className="mt-2 text-slate-600">Generate mapping suggestions in the backend or check your data folders.</p>
        </div>
      ) : (
        <JobsListClient jobs={jobs} />
      )}
    </section>
  );
}
