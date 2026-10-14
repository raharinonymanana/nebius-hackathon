import { useState, useRef, useEffect, useLayoutEffect } from 'react'
import type { ReactNode } from 'react'
import type { Run } from './contract'
import { normaliseRun } from './normalise'

const TARGET = 'ormar'
// Backend budget is ~25s (cold start ~12s). Give the browser headroom above that
// so the backend's own graceful NOT-PROVEN reply wins over a client-side abort.
const TIMEOUT_MS = 30000

type Entry =
  | { id: number; kind: 'banner' }
  | { id: number; kind: 'input'; text: string }
  | { id: number; kind: 'verdict'; run: Run; note: string | null }
  | { id: number; kind: 'error'; message: string }

const BANNER = `Mélodie — runtime proof harness for dependency vulnerabilities
Every verify is a real run: your input is replayed, model-free, in a disposable
Nebius Token Factory Sandbox with a planted canary.

Scope — bounded by design:
  target   ormar 0.22.0 · Product.objects.max() · SQL injection (CVE-2026-26198)
  test     one input string → did the canary leak?
  verdict  PROVEN = exploit confirmed · NOT PROVEN = not confirmed by this input (never "safe")
This confirms a known finding. It does not discover vulnerabilities, scan apps,
or cover arbitrary CVEs.

try   price                                                      (benign)
try   (SELECT password_hash FROM users WHERE username='admin')   (known exploit)
first verify may take ~12s (cold start)`

// About box re-layout: the banner copy is kept VERBATIM, only sliced for colour.
//   head           = build-name line           -> --brand
//   boundary       = the "does / doesn't" honesty sentence -> --fg (not dim)
//   everything else= body                       -> --dim
// Slicing never adds or drops a character, so the G1 boundary text is intact.
const BANNER_HEAD = BANNER.slice(0, BANNER.indexOf('\n'))
const BANNER_REST = BANNER.slice(BANNER.indexOf('\n'))
const BANNER_BOUNDARY =
  'This confirms a known finding. It does not discover vulnerabilities, scan apps,\nor cover arbitrary CVEs.'
const BANNER_BI = BANNER_REST.indexOf(BANNER_BOUNDARY)
const BANNER_PRE = BANNER_REST.slice(0, BANNER_BI)
const BANNER_POST = BANNER_REST.slice(BANNER_BI + BANNER_BOUNDARY.length)

// Verdict presentation, keyed on the exact contract literals (Run['verdict']).
// Colour is never the sole signal: each chip carries a glyph + text label.
const VERDICT_META: Record<
  Run['verdict'],
  { label: string; glyph: string; cls: string }
> = {
  PROVEN: { label: 'PROVEN', glyph: '✓', cls: 'verdict-proven' },
  'NOT PROVEN': { label: 'NOT PROVEN', glyph: '✗', cls: 'verdict-not-proven' },
  'FIX VERIFIED': { label: 'FIX VERIFIED', glyph: '◆', cls: 'verdict-fix-verified' },
}

function Verify({ ledger }: { ledger: ReactNode }) {
  const [input, setInput] = useState('')
  const [entries, setEntries] = useState<Entry[]>(() => [{ id: 0, kind: 'banner' }])
  const [verifying, setVerifying] = useState(false)
  const idRef = useRef(1) // banner took 0; next id starts at 1
  const inputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null) // empty div rendered last, the scroll target
  const scrollIntent = useRef<'always' | 'if-near' | null>(null)
  const wasNearBottom = useRef(false)

  function nextId() {
    return idRef.current++
  }

  function isNearBottom() {
    return window.innerHeight + window.scrollY >= document.body.offsetHeight - 80
  }

  function scrollToBottom() {
    // D4: smooth autoscroll, but honour prefers-reduced-motion (instant then).
    // Behaviour value only — the intent/near-bottom gating refs are unchanged.
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    bottomRef.current?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'end',
    })
  }

  useLayoutEffect(() => {
    if (scrollIntent.current === 'always') {
      scrollToBottom()
    } else if (scrollIntent.current === 'if-near' && wasNearBottom.current) {
      scrollToBottom()
    }
    scrollIntent.current = null
  }, [entries])

  useEffect(() => {
    if (!verifying) inputRef.current?.focus()
  }, [verifying])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (verifying) return
    const text = input
    if (text.trim() === '') return
    scrollIntent.current = 'always'
    setEntries((prev) => [...prev, { id: nextId(), kind: 'input', text }])
    setInput('')
    setVerifying(true)

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
    try {
      const res = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: TARGET, input: text }),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const raw: unknown = await res.json()
      const run = normaliseRun(raw)
      const note =
        raw !== null &&
        typeof raw === 'object' &&
        typeof (raw as Record<string, unknown>).note === 'string'
          ? ((raw as Record<string, unknown>).note as string)
          : null
      wasNearBottom.current = isNearBottom()
      scrollIntent.current = 'if-near'
      setEntries((prev) => [...prev, { id: nextId(), kind: 'verdict', run, note }])
    } catch (err: unknown) {
      const message =
        err instanceof DOMException && err.name === 'AbortError'
          ? `timed out after ${TIMEOUT_MS / 1000}s`
          : err instanceof Error
            ? err.message
            : String(err)
      wasNearBottom.current = isNearBottom()
      scrollIntent.current = 'if-near'
      setEntries((prev) => [...prev, { id: nextId(), kind: 'error', message }])
    } finally {
      clearTimeout(timer)
      setVerifying(false)
    }
  }

  return (
    <>
      {/* row 2 of the pane grid — the ONLY scroll region (overflow-y:auto) */}
      <div className="transcript">
        {entries.map((e) => (
          <div key={e.id} className="entry">
            {e.kind === 'banner' && (
              <section className="about">
                <span className="about-title">ℹ about</span>
                <pre className="about-body">
                  <span className="about-head">{BANNER_HEAD}</span>
                  <span className="about-dim">{BANNER_PRE}</span>
                  <span className="about-boundary">{BANNER_BOUNDARY}</span>
                  <span className="about-dim">{BANNER_POST}</span>
                </pre>
              </section>
            )}
            {e.kind === 'input' && (
              <div className="echo">
                <span className="echo-prefix">❯</span>
                <span className="echo-text">{e.text}</span>
                <span className="echo-run">#{e.id}</span>
              </div>
            )}
            {e.kind === 'verdict' &&
              (() => {
                const v = VERDICT_META[e.run.verdict]
                return (
                  <div className={`result ${v.cls}`}>
                    <div className="result-head">
                      <span className={`chip ${v.cls}`}>
                        {v.glyph} {v.label}
                      </span>
                      {e.note && <span className="result-note">{e.note}</span>}
                    </div>
                    {e.run.verdict === 'PROVEN' && (
                      <div className="entry-trace">
                        {e.run.human_trace.map((step, i) => (
                          <div key={i} className="trace-step">
                            {step}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })()}
            {e.kind === 'error' && (
              <div className="entry-error">
                <span className="err-glyph">⚠</span> error: {e.message}
              </div>
            )}
          </div>
        ))}

        {verifying && (
          <div className="verifying-line">verifying… (cold start ~12s)</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* row 3 of the pane grid — prompt line + status (eval ledger) */}
      <div className="promptbar">
        <form className="prompt-form" onSubmit={onSubmit}>
          <span className="prompt-prefix">❯</span>
          <input
            ref={inputRef}
            className="prompt-input"
            value={input}
            onChange={(ev) => setInput(ev.target.value)}
            maxLength={2000}
            disabled={verifying}
            autoComplete="off"
            spellCheck={false}
            placeholder="type an input, then verify"
          />
          <button type="submit" disabled={verifying || input.trim() === ''}>
            {verifying ? 'verifying…' : 'verify'}
          </button>
        </form>
        <div className="status-line">{ledger}</div>
      </div>
    </>
  )
}

export default Verify
