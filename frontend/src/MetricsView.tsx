import { useEffect, useState } from "react";
import { ApiError, getMetrics } from "./api";
import type { Metrics } from "./types";

export function MetricsView({ apiKey }: { apiKey: string }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setMetrics(null);
    setError(null);
    getMetrics(apiKey)
      .then((body) => {
        if (!cancelled) setMetrics(body);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "Forge didn't respond.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  if (error) {
    return (
      <p className="alert" role="alert">
        {error}
      </p>
    );
  }
  if (!metrics) return <p className="hint">Checking the last review</p>;
  if (metrics.status !== "measured") {
    return <p className="hint">This version has not been reviewed yet.</p>;
  }

  const cards: Array<[string, string]> = [
    ["Got the facts right", percent(metrics.faithfulness)],
    ["Lookups worked", percent(metrics.tool_success_rate)],
    ["Only answered when it should", percent(metrics.decision_accuracy)],
    ["Charge per answer", metrics.estimated_cost_usd_per_success === null ? "—" : "$0"],
  ];

  return (
    <section className="panel">
      <p className="hint">
        Last review of {metrics.tasks} sample questions. This check decides whether the version can be turned on.
      </p>
      <div className="cards">
        {cards.map(([label, value]) => (
          <article key={label}>
            <p>{label}</p>
            <strong>{value}</strong>
          </article>
        ))}
      </div>
      <p className="notes">Nothing is charged for an answer. A weak review keeps this version in practice.</p>
    </section>
  );
}

function percent(value: number | null): string {
  if (value === null) return "—";
  return `${Math.round(value * 100)}%`;
}
