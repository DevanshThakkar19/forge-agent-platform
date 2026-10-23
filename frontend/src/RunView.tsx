import { useRef, useState, type FormEvent } from "react";
import { ApiError, createRun, getRun } from "./api";
import { EXAMPLES, askedNumbers, coversNumbers, guestAnswer, guestStep, sourceName, stepLabel } from "./guest";
import type { RunRecord } from "./types";

export function RunView({ apiKey }: { apiKey: string }) {
  const [query, setQuery] = useState("");
  const [record, setRecord] = useState<RunRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const request = useRef(0);

  function fill(example: string) {
    request.current += 1;
    setQuery(example);
    setRecord(null);
    setError(null);
    setPending(false);
  }

  async function ask(text: string) {
    const sent = text.trim();
    if (!sent || pending) return;
    const id = request.current + 1;
    request.current = id;
    setQuery(sent);
    setPending(true);
    setError(null);
    try {
      const created = await createRun(apiKey, sent, "stub");
      const body = await getRun(apiKey, created.id);
      if (request.current !== id) return;
      setRecord(body);
    } catch (caught) {
      if (request.current !== id) return;
      setRecord(null);
      setError(caught instanceof ApiError ? caught.message : "Forge didn't respond.");
    } finally {
      if (request.current === id) setPending(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(query);
  }

  const guest = record ? guestAnswer(record) : null;
  const numbers = record ? askedNumbers(record.query) : [];
  const shownSources =
    record?.accepted
      ? (record.result?.citations ?? []).filter(
          (cite) => cite.source.startsWith("file:") || coversNumbers(cite.excerpt, numbers),
        )
      : [];

  return (
    <section>
      <form className="panel" onSubmit={onSubmit}>
        <label>
          What should Forge look up?
          <textarea
            value={query}
            rows={3}
            placeholder="Where is order 1001?"
            onChange={(event) => fill(event.target.value)}
          />
        </label>
        <div className="examples">
          <p>Examples</p>
          <div className="asks">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                className={query.trim() === example ? "on" : ""}
                onClick={() => fill(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
        <button className="send" type="submit" disabled={pending || !query.trim()}>
          {pending ? "Checking" : "Ask Forge"}
        </button>
      </form>
      {error ? (
        <p className="alert" role="alert">
          {error}
        </p>
      ) : null}
      {record && guest ? (
        <article className="panel result">
          <p className={`pill ${record.accepted ? "accepted" : "rejected"}`}>{guest.title}</p>
          {guest.lines.map((line) => (
            <p className="answer" key={line}>
              {line}
            </p>
          ))}
          {guest.saved ? <p className="hint">A note was saved.</p> : null}
          <h2>Where this came from</h2>
          {shownSources.length === 0 ? (
            <p className="hint">{record.accepted ? "No record was used." : "No record covers this."}</p>
          ) : (
            <ul className="cites">
              {shownSources.map((cite) => (
                <li key={cite.source}>
                  <p className="source">{sourceName(cite.source)}</p>
                </li>
              ))}
            </ul>
          )}
          <details className="trace">
            <summary>See how this was checked</summary>
            <ol className="steps">
              {record.steps.map((step) => (
                <li key={`${step.node}-${step.detail}`}>
                  <strong>{stepLabel(step.node)}</strong>
                  <span>{guestStep(step.node, step.detail)}</span>
                </li>
              ))}
            </ol>
          </details>
        </article>
      ) : null}
    </section>
  );
}
