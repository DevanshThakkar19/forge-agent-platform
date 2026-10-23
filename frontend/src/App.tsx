import { useEffect, useState } from "react";
import { getHealth } from "./api";
import { MetricsView } from "./MetricsView";
import { RunView } from "./RunView";
import type { Health } from "./types";

type Page = "ask" | "trust";

const KEY = "forge-api-key";

export function App() {
  const [page, setPage] = useState<Page>("ask");
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(KEY) || "dev-api-key");
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    sessionStorage.setItem(KEY, apiKey);
  }, [apiKey]);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((body) => {
        if (!cancelled) {
          setHealth(body);
          setHealthError(null);
        }
      })
      .catch(() => {
        if (!cancelled) setHealthError("unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const desk = !health
    ? healthError
      ? "Forge is having trouble"
      : "Checking Forge"
    : health.status === "ok" && health.database === "ok"
      ? "Forge is up"
      : "Forge is having trouble";

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <p className="eyebrow">Northline support desk</p>
          <h1 className="mark">Forge</h1>
          <p className="tag">Northline runs this desk. An answer shows up only when the records cover it.</p>
        </div>
        <nav className="nav">
          <button type="button" className={page === "ask" ? "on" : ""} onClick={() => setPage("ask")}>
            Ask
          </button>
          <button type="button" className={page === "trust" ? "on" : ""} onClick={() => setPage("trust")}>
            Release check
          </button>
        </nav>
      </header>
      <p className="health">{desk}</p>
      <main>{page === "ask" ? <RunView apiKey={apiKey} /> : <MetricsView apiKey={apiKey} />}</main>
      <details className="staff">
        <summary>Setup</summary>
        <label>
          Key
          <input
            value={apiKey}
            autoComplete="off"
            spellCheck={false}
            onChange={(event) => setApiKey(event.target.value)}
          />
        </label>
      </details>
    </div>
  );
}
