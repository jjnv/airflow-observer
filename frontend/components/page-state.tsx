export function PageError({ title, message }: { title: string; message?: string }) {
  return (
    <section className="card p-6">
      <p className="text-sm font-medium text-red-700">Unable to load data</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-muted">
        {message || "Check that the Observer backend is running and reachable from the frontend container."}
      </p>
    </section>
  );
}
