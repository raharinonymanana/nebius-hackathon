import type { Run } from '../lib/contract'
import { VERDICT_META } from '../lib/verdict'

export function RunResult({
  run,
  note,
  isLatest,
}: {
  run: Run
  note: string | null
  isLatest: boolean
}) {
  const v = VERDICT_META[run.verdict]
  const isReplay = !!note && note.startsWith('[replay')
  // Prefer structured steps[] when the run carries them; else fall
  // back to the flat human_trace (PROVEN-only). Captured as consts so
  // any narrowing survives inside the .map callbacks below.
  const steps = run.steps ?? null
  const trace =
    run.verdict === 'PROVEN' ? run.human_trace : null
  // Structured-trace summary bits (only consumed when steps render).
  const decidedIdx = steps ? steps.findIndex((s) => s.decided) : -1
  const stopped = steps
    ? steps.some((s) => s.status === 'skipped')
    : false
  return (
    <div className={`result ${v.cls}`}>
      <p className="verdict">
        <span className="chip">
          <span aria-hidden="true">{v.glyph} </span>
          {v.label}
        </span>
        {note && <span>{note}</span>}
      </p>
      {/* Canary token — surfaced verbatim as the run's evidence.
          Rendered on any verdict (PROVEN / NOT PROVEN); never on the
          RUN FAILED branch, which is a separate return below. */}
      {run.canary && (
        <>
          <p className="meta">
            canary{' '}
            <span className="canary-token">{run.canary}</span>
          </p>
          {!isReplay && run.verdict === 'PROVEN' && (
            <p className="meta canary-proof">
              This secret was generated for your run and found leaked inside the
              sealed sandbox — run it again and the token changes.
            </p>
          )}
        </>
      )}
      {!isReplay && run.verdict === 'NOT PROVEN' && (
        <p className="meta notproven-note">
          The harness ran and correctly did not prove this input — a NOT PROVEN is
          the harness working, not a failure.
        </p>
      )}
      {steps && steps.length > 0 ? (
        <details
          className="trace"
          {...(isLatest ? { open: true } : {})}
        >
          <summary>
            trace · {steps.length} step
            {steps.length === 1 ? '' : 's'}
            {decidedIdx >= 0
              ? ` · ${stopped ? 'stopped' : 'decided'} at step ${decidedIdx + 1}`
              : ''}
          </summary>
          <ol className={isLatest ? 'steps reveal' : 'steps'}>
            {steps.map((s, i) => {
              const last = i === steps.length - 1
              const glyph =
                s.status === 'ok'
                  ? '✓'
                  : s.status === 'fail'
                    ? '✗'
                    : '·'
              return (
                <li
                  key={i}
                  className={s.decided ? 'key' : undefined}
                  style={{ ['--i']: i } as React.CSSProperties}
                >
                  <span aria-hidden="true">
                    {last ? '└─' : '├─'}
                  </span>
                  <span className="s">{glyph}</span>
                  <span>
                    {s.name}
                    {s.decided ? (
                      <span className="why">← decided</span>
                    ) : null}
                  </span>
                  <span className="dur">
                    {s.seconds != null
                      ? `${s.seconds.toFixed(1)}s`
                      : ''}
                  </span>
                </li>
              )
            })}
          </ol>
        </details>
      ) : trace ? (
        <details
          className="trace"
          {...(isLatest ? { open: true } : {})}
        >
          <summary>
            trace · {trace.length} step
            {trace.length === 1 ? '' : 's'}
          </summary>
          <ol className="steps">
            {trace.map((step, i) => {
              const last = i === trace.length - 1
              return (
                <li key={i}>
                  <span aria-hidden="true">
                    {last ? '└─' : '├─'}
                  </span>
                  <span className="s" />
                  <span>{step}</span>
                  <span className="dur" />
                </li>
              )
            })}
          </ol>
        </details>
      ) : null}
      {!isReplay && (
        <p className="meta eval-pointer">
          Want the measured evidence behind the harness? Type{' '}
          <span className="g">/eval</span> for pass@k rates across all classes.
        </p>
      )}
    </div>
  )
}

export function RunFailed({ message }: { message: string }) {
  // kind === 'error' — a RUN FAILED is NOT a verdict: dashed rail +
  // outlined chip set it apart from PROVEN / NOT PROVEN.
  return (
    <div className="result is-fail">
      <p className="verdict">
        <span className="chip chip-outline">
          <span aria-hidden="true">! </span>RUN FAILED
        </span>
        <span>{message} — not a verdict</span>
      </p>
    </div>
  )
}
