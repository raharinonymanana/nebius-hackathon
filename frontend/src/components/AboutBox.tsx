import type { Contract, Run, Target } from '../lib/contract'
import { TARGET } from '../lib/config'
import { evalRate } from '../lib/commands'
import { AsciiArt } from './AsciiArt'
import { WORDMARK_BOLD } from '../lib/melodie-art'

// One TRY IT gallery shot: a payload the user can fire. `live` shots POST
// /api/verify; replay shots push a stored run with a [replay] note.
type Shot = { payload: string; tag: string; live: boolean; run: () => void }

export function AboutBox({
  contract,
  verifying,
  runLive,
  runReplay,
}: {
  contract: Contract | null
  verifying: boolean
  runLive: (text: string) => void
  runReplay: (run: Run | null) => void
}) {
  // TRY IT gallery shots, built from the loaded contract. Two LIVE
  // shots POST /api/verify (ormar); three REPLAY shots push a stored
  // contract run (starlette / gitpython). Empty until contract loads.
  const ormar = contract?.targets.find((t: Target) =>
    t.id.startsWith('ormar'),
  )
  const starlette = contract?.targets.find((t: Target) =>
    t.id.startsWith('starlette'),
  )
  const gitpython = contract?.targets.find((t: Target) =>
    t.id.startsWith('gitpython'),
  )
  const shots: Shot[] = []
  if (ormar) {
    const sql = ormar.runs.proven.input ?? ''
    shots.push({ payload: sql, tag: 'SQL injection · expect PROVEN', live: true, run: () => runLive(sql) })
    shots.push({ payload: 'price', tag: 'benign control · expect NOT PROVEN', live: true, run: () => runLive('price') })
  }
  if (starlette) {
    const pr = starlette.runs.proven
    shots.push({ payload: pr.input ?? '', tag: 'path traversal · PROVEN', live: false, run: () => runReplay(pr) })
  }
  if (gitpython) {
    const pr = gitpython.runs.proven
    shots.push({ payload: pr.input ?? '', tag: 'command injection · PROVEN (handed)', live: false, run: () => runReplay(pr) })
  }
  if (starlette) {
    const fv = starlette.runs.fix_verified
    shots.push({ payload: fv.input ?? '(patched target)', tag: 'same exploit, patched · FIX VERIFIED', live: false, run: () => runReplay(fv) })
  }
  return (
    <section
      className="box about"
      aria-labelledby="about-h"
    >
      <h2 className="box-title" id="about-h">
        about
      </h2>
      {/* Splash row: the text column is the hero (left, flexes),
          WORDMARK_BOLD parked top-right (space-between, top-aligned,
          nudged off the border by .splash-mark padding). Wordmark is
          hidden ≤640px; the text column then goes full width. Still a
          transcript entry — it scrolls with the log. */}
      <div className="splash-row">
        <div className="about-hero">
          {/* BLOCK 1 — name + lede (prose: the only wrapping text). */}
          <p className="hero-name">Mélodie</p>
          <p className="hero-lede">
            Replays a{' '}
            <span className="g">proof-of-concept</span> in a sealed{' '}
            <span className="g">Nebius Token Factory</span> sandbox,
            <br />
            canary-checked, and returns{' '}
            <span className="g em">PROVEN</span> /{' '}
            <span className="r em">NOT PROVEN</span> with a full trace.
          </p>
          {/* BLOCK 3 — try-it: interactive gallery. LIVE shots POST
              /api/verify; REPLAY shots push a stored receipt run. */}
          <p className="try-head dim">TRY IT</p>
          <p className="try-lead">
            Type your own input in the prompt below and press{' '}
            <kbd>⏎</kbd> — it runs live against a sealed sandbox.{' '}
            <span className="dim">Live class: SQL injection. Try{' '}
            <span className="g">(SELECT password_hash FROM users WHERE username='admin')</span>,
            or <span className="r">any string</span>.</span>
          </p>
          {shots.length > 0 ? (
            (() => {
              const liveShots = shots.filter((s) => s.live)
              const replayShots = shots.filter((s) => !s.live)
              return (
                <>
                  {liveShots.length > 0 && (
                    <>
                      <p className="shots-group dim">try it live</p>
                      <ul className="shots">
                        {liveShots.map((s, i) => (
                          <li key={i}>
                            <button
                              type="button"
                              className="shot"
                              onClick={s.run}
                              disabled={verifying}
                            >
                              <span className={s.live ? 'chip' : 'chip chip-outline'}>
                                {s.live ? 'LIVE' : 'REPLAY'}
                              </span>
                              <span className="shot-payload">{s.payload}</span>
                              <span className="shot-tag dim">
                                {i === 0 ? (
                                  <>
                                    SQL injection or{' '}
                                    <span className="fg">
                                      any other string
                                    </span>
                                    .{s.tag.slice('SQL injection'.length)}
                                  </>
                                ) : (
                                  s.tag
                                )}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {replayShots.length > 0 && (
                    <>
                      <p className="shots-group dim">recorded runs</p>
                      <ul className="shots">
                        {replayShots.map((s, i) => (
                          <li key={i}>
                            <button
                              type="button"
                              className="shot"
                              onClick={s.run}
                              disabled={verifying}
                            >
                              <span className={s.live ? 'chip' : 'chip chip-outline'}>
                                {s.live ? 'LIVE' : 'REPLAY'}
                              </span>
                              <span className="shot-payload">{s.payload}</span>
                              <span className="shot-tag dim">{s.tag}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )
            })()
          ) : (
            <span className="dim">loading…</span>
          )}
          {/* BLOCK 2a — SUPPORTED CLASSES: all three target cards
              from the loaded contract. LIVE is the target the live
              /api/verify POST hits (TARGET); the rest are REPLAY. */}
          {contract ? (
            <div className="supported">
              <span className="dim supported-label">
                SUPPORTED CLASSES
              </span>
              <ul className="classes">
                {contract.targets.map((t) => {
                  const live = t.id.startsWith(TARGET)
                  const rate = evalRate(contract.eval, t.id)
                  return (
                    <li key={t.id} className="class-row">
                      <span
                        className={live ? 'chip' : 'chip chip-outline'}
                      >
                        {live ? 'LIVE' : 'REPLAY'}
                      </span>
                      <span className="class-name">
                        {t.exploit_class}
                      </span>
                      <span className="class-cve">{t.cve}</span>
                      <span className="class-ver dim">
                        {t.vulnerable_version} → {t.fixed_version}
                      </span>
                      {rate ? (
                        <span className="class-rate dim">{rate}</span>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </div>
          ) : (
            <span className="dim">loading classes…</span>
          )}
          {/* BLOCK 2 — spec grid (fixed label column, --fg values). */}
          <dl className="spec">
            <dt className="dim">STACK</dt>
            <dd>
              <span className="mk4">
                Nebius Token Factory Sandboxes (ConTree)
              </span>{' '}
              <span className="dim">·</span> model-free replay
            </dd>
            <dt className="dim">SCOPE</dt>
            <dd>
              confirms a <span className="g">KNOWN</span> finding — not
              discovery, scanning, or arbitrary CVEs
            </dd>
          </dl>
          {/* BLOCK 2b — ADVISORY: Tavily-retrieved context per CVE.
              Scored + filtered; the verdict never depends on it. Folded
              (click-to-expand, like a trace) and placed last — least
              load-bearing, tucked out of the 2-second read. */}
          {contract ? (
            <details className="trace advisory-fold">
              <summary>ADVISORY · via Tavily</summary>
              <div className="advisory-note">
                <ul className="advisories">
                  {contract.targets.map((t) => {
                    const a = t.runs.proven.advisory
                    if (!a || !a.top_source) return null
                    const host = a.top_source.url
                      .replace(/^https?:\/\//, '')
                      .split('/')[0]
                    return (
                      <li key={t.id} className="advisory-row">
                        <span className="class-cve">{a.cve}</span>
                        <a
                          className="advisory-link"
                          href={a.top_source.url}
                          target="_blank"
                          rel="noreferrer noopener"
                        >
                          {host} ↗
                        </a>
                        <span className="dim">
                          score {a.top_source.score.toFixed(2)} ·{' '}
                          {a.discarded_count} discarded
                        </span>
                      </li>
                    )
                  })}
                </ul>
                <span className="dim advisory-foot">
                  Context only — the verdict comes from the replay
                  harness, never the advisory.
                </span>
              </div>
            </details>
          ) : null}
        </div>
        <div className="splash-mark">
          <AsciiArt piece={WORDMARK_BOLD} />
        </div>
      </div>
    </section>
  )
}
