import Link from "next/link";

import { PageError } from "@/components/page-state";
import { getRecommendations, seconds } from "@/lib/api";

export default async function RecommendationsPage() {
  let data: Awaited<ReturnType<typeof getRecommendations>>;
  try {
    data = await getRecommendations();
  } catch (error) {
    return <PageError title="Recommendations are unavailable" message={error instanceof Error ? error.message : undefined} />;
  }
  const { recommendations } = data;

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-muted">Prioritized fixes</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Recommendations</h1>
      </section>

      <section className="grid gap-3">
        {recommendations.map((recommendation, index) => (
          <article key={recommendation.id} className="card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-sm text-muted">#{index + 1}</div>
                <Link
                  className="mt-1 block font-semibold text-accent hover:underline"
                  href={`/dags/${encodeURIComponent(recommendation.dag_id)}`}
                >
                  {recommendation.title}
                </Link>
                <p className="mt-1 text-sm text-muted">
                  {recommendation.dag_id}
                  {recommendation.task_id ? ` / ${recommendation.task_id}` : ""}
                </p>
              </div>
              <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium uppercase text-blue-700 ring-1 ring-blue-200">
                {recommendation.impact}
              </span>
            </div>
            <p className="mt-3 text-sm">{recommendation.reason}</p>
            <p className="mt-2 text-xs text-muted">
              Type: {recommendation.kind} · Evidence: {recommendation.evidence_count} · Estimated saving:{" "}
              {seconds(recommendation.estimated_savings_seconds)}
            </p>
          </article>
        ))}
        {recommendations.length === 0 ? (
          <div className="card p-6 text-sm text-muted">No recommendations found.</div>
        ) : null}
      </section>
    </div>
  );
}
