export default function HomePage() {
  return (
    <div className="bg-white border rounded-xl p-8">
      <h1 className="text-3xl font-bold">Mapping UI</h1>
      <p className="mt-2 text-slate-600">Validate AI mapping suggestions and save approved mappings.</p>

      <a
        href="/mapping"
        className="inline-block mt-6 px-4 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800"
      >
        Go to Mapping Jobs
      </a>
    </div>
  );
}
