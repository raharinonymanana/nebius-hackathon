import { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'
import type { Run, Contract, Target } from './contract'
import { normaliseRun } from './normalise'
import { WIDE_CHARS, useBlockCursor, useRotatingVerb, Verb } from './terminal-hooks'
import { AsciiArt } from './AsciiArt'
import { WORDMARK_BOLD } from './melodie-art'

const TARGET = 'ormar'
// Backend budget is ~25s (cold start ~12s). Give the browser headroom above that
// so the backend's own graceful NOT-PROVEN reply wins over a client-side abort.
const TIMEOUT_MS = 30000

type Entry =
  | { id: number; kind: 'banner' }
  | { id: number; kind: 'input'; text: string }
  | { id: number; kind: 'verdict'; run: Run; note: string | null }
  | { id: number; kind: 'error'; message: string }
  | { id: number; kind: 'help' }
  | { id: number; kind: 'notice'; text: string }
  | { id: number; kind: 'output'; title: string; body: string }

// One TRY IT gallery shot: a payload the user can fire. `live` shots POST
// /api/verify; replay shots push a stored run with a [replay] note.
type Shot = { payload: string; tag: string; live: boolean; run: () => void }


// /help output. Lists ONLY what is actually built — no invented commands, no
// unbuilt keys (e.g. esc). Kept in sync with onSubmit's slash dispatch below.
const HELP = `commands
  /help      show this help
  /clear     clear the transcript
  /eval      evaluation table (pass@k, Wilson 95%)
  /classes   supported CVE classes + status
  /receipts  replay receipts on disk
  /scope     what Mélodie does and does not do
  /version   build + data provenance
keys
  ⏎          verify the current input
  ↑ / ↓      walk input history`

// Verdict presentation, keyed on the exact contract literals (Run['verdict']).
// Colour is never the sole signal: each chip carries a glyph + text label. The
// class is the RESULT class (sets --rail); the chip itself is just .chip.
// FIX VERIFIED is dead in the live verify flow (the backend returns only
// PROVEN / NOT PROVEN); its entry stays only to satisfy the Record type.
const VERDICT_META: Record<
  Run['verdict'],
  { label: string; glyph: string; cls: string }
> = {
  PROVEN: { label: 'PROVEN', glyph: '✓', cls: 'is-proven' },
  'NOT PROVEN': { label: 'NOT PROVEN', glyph: '✗', cls: 'is-not-proven' },
  'FIX VERIFIED': { label: 'FIX VERIFIED', glyph: '◆', cls: 'is-proven' },
}

// Transcript persistence (sessionStorage — per-tab, cleared when the tab closes).
// Only `entries` is persisted; every other piece of state stays transient. The key
// is versioned so a future shape change can invalidate old data cleanly.
const TRANSCRIPT_KEY = 'melodie.transcript.v1'
const DEFAULT_ENTRIES: Entry[] = [{ id: 0, kind: 'banner' }]

// Lazy initializer for `entries`. Reads sessionStorage defensively: any parse error,
// wrong shape, or empty array falls back to the banner-only default, and a corrupt
// value is dropped so it can't wedge every future load. Never throws (storage access
// itself can throw in private-mode / blocked-cookie contexts).
function loadEntries(): Entry[] {
  try {
    const raw = sessionStorage.getItem(TRANSCRIPT_KEY)
    if (!raw) return DEFAULT_ENTRIES
    const parsed = JSON.parse(raw)
    const ok =
      Array.isArray(parsed) &&
      parsed.length > 0 &&
      parsed.every(
        (e) => e && typeof e.id === 'number' && typeof e.kind === 'string',
      )
    if (!ok) {
      sessionStorage.removeItem(TRANSCRIPT_KEY)
      return DEFAULT_ENTRIES
    }
    return parsed as Entry[]
  } catch {
    return DEFAULT_ENTRIES
  }
}

// Headline eval rate for a target card, if the eval table carries one.
// Self-labeling (the axis names itself), returns null when none applies
// (e.g. a handed target with no unaided rate). Reads loaded data only.
function evalRate(ev: Contract['eval'], targetId: string): string | null {
  const short = targetId.split('-')[0]
  for (const kw of ['weaponise', 'locate']) {
    const r = ev.rows.find(
      (row) =>
        row.kind === 'rate' &&
        row.target === short &&
        row.axis.includes(kw) &&
        row.ci_lo !== null,
    )
    if (r && r.kind === 'rate') {
      const label = r.axis.split(' ')[0]
      return `${label} ${r.rate_str} ${r.ci_str}`
    }
  }
  return null
}

// --- Data slash-commands. Each renders through the 'output' entry kind and reads
// only the already-loaded Contract (no model / API / Tavily call). ---

const SCOPE_BODY = `Mélodie confirms a KNOWN finding by replaying a proof-of-concept
in a sealed, model-free sandbox and canary-checking the result.

IT IS      exploit validation — PROVEN / NOT PROVEN / FIX VERIFIED,
           decided only by the canary, never by a model.
IT IS NOT  discovery, scanning, fuzzing, or arbitrary-CVE coverage.

Supported classes: SQL injection, path traversal, command injection.`

function evalBody(c: Contract): string {
  const ev = c.eval
  const tW = Math.max(8, ...ev.rows.map((r) => r.target.length))
  const aW = Math.max(8, ...ev.rows.map((r) => r.axis.length))
  const lines: string[] = []
  const sections: string[] = []
  for (const r of ev.rows) if (!sections.includes(r.section)) sections.push(r.section)
  for (const sec of sections) {
    lines.push(sec.toUpperCase())
    for (const r of ev.rows.filter((x) => x.section === sec)) {
      const val = r.ci_str ? `${r.rate_str}  ${r.ci_str}` : r.rate_str
      lines.push(`  ${r.target.padEnd(tW)}  ${r.axis.padEnd(aW)}  ${val}`)
    }
    lines.push('')
  }
  if (ev.remediation.length) {
    lines.push('REMEDIATION')
    const rW = Math.max(8, ...ev.remediation.map((r) => r.target.length))
    for (const rm of ev.remediation) {
      const verdict = rm.verified ? 'FIX VERIFIED' : 'FIX NOT VERIFIED'
      const attempt = `attempt ${rm.first_verified_attempt}/${rm.attempts}`
      lines.push(
        `  ${rm.target.padEnd(rW)}  ${verdict.padEnd(16)}  ${attempt}${rm.note ? '  — ' + rm.note : ''}`,
      )
    }
    lines.push('')
  }
  if (ev.notes.length) {
    lines.push('NOTES')
    for (const n of ev.notes) lines.push(`  · ${n}`)
  }
  return lines.join('\n').trimEnd()
}

function classesBody(c: Contract): string {
  return c.targets
    .map((t) => {
      const status = t.id.startsWith(TARGET) ? 'LIVE' : 'REPLAY'
      const rate = evalRate(c.eval, t.id) ?? '—'
      return [
        `${t.cve}  [${status}]`,
        `  class     ${t.exploit_class}`,
        `  version   ${t.vulnerable_version} → ${t.fixed_version}`,
        `  unaided   ${rate}`,
      ].join('\n')
    })
    .join('\n\n')
}

function receiptsBody(c: Contract): string {
  const m = c.meta
  const lines: string[] = [
    `${m.receipts_valid} valid receipts (${m.receipts_excluded} excluded) · model-free replay`,
    '',
  ]
  for (const t of c.targets) {
    lines.push(t.cve)
    const rows: Array<[string, { verdict: string; source_receipt: string } | null]> = [
      ['proven', t.runs.proven],
      ['not_proven', t.runs.not_proven],
      ['fix_verified', t.runs.fix_verified],
    ]
    for (const [label, run] of rows) {
      if (run) lines.push(`  ${label.padEnd(12)} ${run.verdict.padEnd(13)} ${run.source_receipt}`)
    }
    lines.push('')
  }
  return lines.join('\n').trimEnd()
}

function versionBody(c: Contract): string {
  const m = c.meta
  return [
    `schema        v${c.schema_version}`,
    `data built    ${c.generated_utc}`,
    `receipts      ${m.receipts_valid} valid, ${m.receipts_excluded} excluded`,
    `model calls   ${m.model_calls}`,
    `model cost    $${m.model_cost_usd.toFixed(2)}`,
    `tavily        ${m.tavily_credits} credits`,
  ].join('\n')
}

function buildCommand(name: string, c: Contract): { title: string; body: string } {
  switch (name) {
    case 'eval': return { title: 'eval', body: evalBody(c) }
    case 'classes': return { title: 'classes', body: classesBody(c) }
    case 'receipts': return { title: 'receipts', body: receiptsBody(c) }
    case 'scope': return { title: 'scope', body: SCOPE_BODY }
    case 'version': return { title: 'version', body: versionBody(c) }
    default: return { title: name, body: '' }
  }
}

function Verify({
  ledger,
  statusSlot,
  contract,
}: {
  ledger: ReactNode
  statusSlot: HTMLElement | null
  contract: Contract | null
}) {
  const [input, setInput] = useState('')
  const [entries, setEntries] = useState<Entry[]>(loadEntries)
  const [verifying, setVerifying] = useState(false)
  const [elapsedMs, setElapsedMs] = useState(0) // ephemeral spinner timer, not logged
  // Seed past the max restored id so new entries never collide with persisted ones
  // (banner took 0 on a fresh load; nextId()'s increment logic is unchanged).
  const idRef = useRef(entries.reduce((m, e) => Math.max(m, e.id), 0) + 1)
  // Block cursor (HANDOFF §9): owns the input ref + the sibling .cursor ref, and
  // positions the block at caret index × 1ch. inputRef also serves the focus effect.
  const { inputRef, cursorRef, place } = useBlockCursor(input)
  // Running-state verb: rotates every 3s through step-agnostic phrases while a
  // verify is in flight (honours reduced-motion internally). Keyed on the real
  // in-flight boolean; the hook takes no step param, so it can't name a phase.
  const runVerb = useRotatingVerb(verifying)
  // ↑/↓ input history (in-memory, this session only — no storage). histIdx === null
  // means the live draft is showing; otherwise it indexes `history` (derived below).
  // draftRef stashes the live draft while walking history, so stepping ↓ past the
  // newest entry restores exactly what the user was typing.
  const [histIdx, setHistIdx] = useState<number | null>(null)
  const draftRef = useRef('')
  const bottomRef = useRef<HTMLDivElement>(null) // empty div rendered last, the scroll target
  const containerRef = useRef<HTMLDivElement>(null) // .transcript — the scroll region (overflow-y:auto)
  // On a restored (non-empty) transcript, the first layout pass jumps to the latest
  // run; a fresh load starts neutral. Reuses the existing scrollIntent → scrollToBottom
  // path (the [entries] layout effect below), not a separate scroll mechanism.
  const scrollIntent = useRef<'always' | 'if-near' | null>(
    entries.length > 1 ? 'always' : null,
  )
  const wasNearBottom = useRef(false)

  function nextId() {
    return idRef.current++
  }

  function isNearBottom() {
    const el = containerRef.current
    if (!el) return true
    return el.scrollTop + el.clientHeight >= el.scrollHeight - 80
  }

  function scrollToBottom() {
    // D4: smooth autoscroll, but honour prefers-reduced-motion (instant then).
    // Behaviour value only — the intent/near-bottom gating refs are unchanged.
    const el = containerRef.current
    if (!el) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollTo({
      top: el.scrollHeight,
      behavior: reduceMotion ? 'auto' : 'smooth',
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

  // Persist the transcript on every change. sessionStorage can throw (quota,
  // private mode, blocked storage), so the write is best-effort — a failure
  // never breaks the live session, it just means no restore after reload.
  useEffect(() => {
    try {
      sessionStorage.setItem(TRANSCRIPT_KEY, JSON.stringify(entries))
    } catch {
      // ignore — persistence is a convenience, not a correctness guarantee
    }
  }, [entries])

  useEffect(() => {
    if (!verifying) inputRef.current?.focus()
  }, [verifying])

  // After a history recall, drop the caret at the end of the recalled text and
  // resync the block cursor. Keyed on histIdx so it fires only on a recall step;
  // it sets the selection, never the value, so it does not fight the controlled input.
  useLayoutEffect(() => {
    if (histIdx === null) return
    const el = inputRef.current
    if (!el) return
    const end = el.value.length
    el.setSelectionRange(end, end)
    place()
  }, [histIdx, place])

  // Live elapsed timer for the in-flight spinner. Ephemeral UI state ONLY — it
  // never touches entries / idRef / the append-only log. Ticks ~10x/s while a
  // verify is in flight; a number updating is not vestibular motion, so it keeps
  // ticking under prefers-reduced-motion (only the spinner glyph freezes, via CSS).
  useEffect(() => {
    if (!verifying) return
    const start = Date.now()
    setElapsedMs(0)
    const id = setInterval(() => setElapsedMs(Date.now() - start), 100)
    return () => clearInterval(id)
  }, [verifying])

  // The live verify run, callable from the typed-input path AND the TRY IT
  // gallery. Pushes the input echo, flips the spinner, POSTs /api/verify and
  // appends the real verdict (or a RUN FAILED error). Identical behaviour to
  // the old inline onSubmit tail — just extracted so a gallery shot can fire it.
  async function runLive(text: string) {
    scrollIntent.current = 'always'
    setEntries((prev) => [...prev, { id: nextId(), kind: 'input', text }])
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

  // Replay a stored contract run instantly (no network): push its input echo
  // then its verdict, tagged [replay · receipt YYYY-MM-DD] so it's never
  // mistaken for a fresh live run.
  function runReplay(run: Run | null) {
    if (!run) return
    const date = run.utc ? run.utc.slice(0, 10) : 'receipt'
    scrollIntent.current = 'always'
    setEntries((prev) => [
      ...prev,
      { id: nextId(), kind: 'input', text: run.input ?? '(replay)' },
      { id: nextId(), kind: 'verdict', run, note: `[replay · receipt ${date}]` },
    ])
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (verifying) return
    const text = input
    if (text.trim() === '') return
    // Slash-commands are handled entirely client-side — they never POST /api/verify.
    const trimmed = text.trim()
    if (trimmed.startsWith('/')) {
      const name = trimmed.slice(1).split(/\s+/)[0].toLowerCase()
      setInput('')
      setHistIdx(null)
      draftRef.current = ''
      if (name === 'clear') {
        idRef.current = 1 // back to a fresh id sequence (banner is 0)
        try {
          sessionStorage.removeItem(TRANSCRIPT_KEY)
        } catch {
          // ignore — nothing to restore anyway
        }
        scrollIntent.current = 'always'
        setEntries([{ id: 0, kind: 'banner' }])
        return
      }
      scrollIntent.current = 'always'
      if (name === 'help') {
        setEntries((prev) => [
          ...prev,
          { id: nextId(), kind: 'input', text: trimmed },
          { id: nextId(), kind: 'help' },
        ])
      } else if (['eval', 'classes', 'receipts', 'scope', 'version'].includes(name)) {
        if (!contract) {
          setEntries((prev) => [
            ...prev,
            { id: nextId(), kind: 'input', text: trimmed },
            { id: nextId(), kind: 'notice', text: 'data still loading — try again in a moment' },
          ])
        } else {
          const { title, body } = buildCommand(name, contract)
          setEntries((prev) => [
            ...prev,
            { id: nextId(), kind: 'input', text: trimmed },
            { id: nextId(), kind: 'output', title, body },
          ])
        }
      } else {
        setEntries((prev) => [
          ...prev,
          { id: nextId(), kind: 'input', text: trimmed },
          {
            id: nextId(),
            kind: 'notice',
            text: `unknown command: /${name} — try /help`,
          },
        ])
      }
      return
    }
    setInput('')
    setHistIdx(null) // leaving history mode: next ↑ starts from the newest entry
    draftRef.current = ''
    await runLive(text)
  }

  // Submitted inputs, oldest→newest — derived from entries, not a second state array.
  const history = entries
    .filter((e): e is Extract<Entry, { kind: 'input' }> => e.kind === 'input')
    .map((e) => e.text)

  // ↑/↓ walk submitted-input history. Enter is deliberately NOT handled here — the
  // native <form onSubmit> owns submit. Typing (onChange) and submit both reset
  // histIdx to null, so history is always re-entered from the newest entry.
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowUp') {
      if (history.length === 0) return // nothing to recall — let the caret move
      e.preventDefault()
      let next: number
      if (histIdx === null) {
        draftRef.current = input // stash the live draft before walking back
        next = history.length - 1
      } else {
        next = Math.max(0, histIdx - 1)
      }
      setHistIdx(next)
      setInput(history[next])
    } else if (e.key === 'ArrowDown') {
      if (histIdx === null) return // already on the live draft — let the caret move
      e.preventDefault()
      if (histIdx < history.length - 1) {
        const next = histIdx + 1
        setHistIdx(next)
        setInput(history[next])
      } else {
        setHistIdx(null) // stepped past the newest → restore the stashed draft
        setInput(draftRef.current)
      }
    }
  }

  // Title-bar status — DERIVED each render from entries/verifying; nothing is
  // stored (no new counter state, no field on Entry). "runs" = completed verify
  // attempts (PROVEN + NOT PROVEN). A failed run is neither ✓ nor ✗, so it is
  // NOT folded into "runs"; it gets its own "! n" bucket (D30). FIX VERIFIED is
  // intentionally not a tally bucket.
  const proven = entries.filter(
    (e) => e.kind === 'verdict' && e.run.verdict === 'PROVEN',
  ).length
  const notProven = entries.filter(
    (e) => e.kind === 'verdict' && e.run.verdict === 'NOT PROVEN',
  ).length
  const failed = entries.filter((e) => e.kind === 'error').length
  const runs = proven + notProven
  // While a verify is in flight the mode shows the SAME number as that run's echo
  // row (the id of the most recent input entry). It is rendered with the exact
  // same expression the echo uses — a bare #{id}, no padding — so the two formats
  // can never diverge.
  const inFlightId = entries.reduce(
    (acc, e) => (e.kind === 'input' ? e.id : acc),
    0,
  )
  // Spinner elapsed: one decimal under 10s (e.g. "3.2s"), whole seconds beyond.
  const elapsedSeconds = elapsedMs / 1000
  const elapsedLabel =
    elapsedSeconds < 10
      ? `${elapsedSeconds.toFixed(1)}s`
      : `${Math.floor(elapsedSeconds)}s`
  // Cold-start hint rides the FIRST verify of the session only (one input entry so
  // far — the in-flight one). Honest: only the backend's first call is cold.
  const isFirstRun = entries.filter((e) => e.kind === 'input').length <= 1

  return (
    <>
      {/* Live title-bar status, portalled into App's title-bar slot (display:
          contents, so .tally + .mode sit as direct flex children of .top).
          Derived above; appears only once App has lent us the slot. */}
      {statusSlot &&
        createPortal(
          <>
            <p className="tally" aria-label="Session tally">
              {runs === 0 && failed === 0 ? (
                <span className="dim">no runs yet</span>
              ) : (
                <>
                  {runs > 0 && (
                    <span className="wide">
                      {runs} run{runs === 1 ? '' : 's'}
                    </span>
                  )}
                  {proven > 0 && (
                    <span>
                      <span className="g" aria-hidden="true">
                        ✓
                      </span>{' '}
                      {proven}
                      <span className="sr-only"> proven</span>
                    </span>
                  )}
                  {notProven > 0 && (
                    <span>
                      <span className="r" aria-hidden="true">
                        ✗
                      </span>{' '}
                      {notProven}
                      <span className="sr-only"> not proven</span>
                    </span>
                  )}
                  {failed > 0 && (
                    <span>
                      <span aria-hidden="true">!</span> {failed}
                      <span className="sr-only"> run failed</span>
                    </span>
                  )}
                </>
              )}
            </p>
            <span
              className={`mode${verifying ? ' is-busy' : ''}`}
              role="status"
            >
              {verifying ? <>RUNNING #{inFlightId}</> : 'READY'}
            </span>
          </>,
          statusSlot,
        )}

      {/* ROW 2 — transcript: the ONLY scroll region. containerRef stays on
          .transcript (the scroller), NOT the inner .log. */}
      <section
        className="transcript"
        role="log"
        aria-label="Session transcript"
        ref={containerRef}
      >
        <div className="log">
          {entries.map((e, idx) => {
            if (e.kind === 'banner') {
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
                  key={e.id}
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
                        canary-checked, and returns{' '}
                        <span className="g em">PROVEN</span> /{' '}
                        <span className="r em">NOT PROVEN</span> with a full trace.
                      </p>
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
                      {/* BLOCK 2b — ADVISORY: the Tavily-retrieved context per
                          CVE. Scored + filtered; the verdict never depends on it. */}
                      {contract ? (
                        <div className="advisory-note">
                          <span className="dim supported-label">
                            ADVISORY · via Tavily
                          </span>
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
                      ) : null}
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
                      {/* BLOCK 3 — try-it: interactive gallery. LIVE shots POST
                          /api/verify; REPLAY shots push a stored receipt run. */}
                      <p className="try-head dim">TRY IT</p>
                      {shots.length > 0 ? (
                        <ul className="shots">
                          {shots.map((s, i) => (
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
                      ) : (
                        <span className="dim">loading…</span>
                      )}
                    </div>
                    <div className="splash-mark">
                      <AsciiArt piece={WORDMARK_BOLD} />
                    </div>
                  </div>
                </section>
              )
            }
            if (e.kind === 'help') {
              return (
                <section
                  key={e.id}
                  className="box about"
                  aria-labelledby={`help-h-${e.id}`}
                >
                  <h2 className="box-title" id={`help-h-${e.id}`}>
                    help
                  </h2>
                  {/* HELP rendered verbatim — dim, whitespace preserved, same
                      monospace block treatment as the banner above. */}
                  <pre
                    className="dim"
                    style={{
                      margin: 0,
                      font: 'inherit',
                      whiteSpace: 'pre-wrap',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {HELP}
                  </pre>
                </section>
              )
            }
            if (e.kind === 'output') {
              return (
                <section
                  key={e.id}
                  className="box about"
                  aria-labelledby={`out-h-${e.id}`}
                >
                  <h2 className="box-title" id={`out-h-${e.id}`}>
                    {e.title}
                  </h2>
                  <pre className="cmd-out dim" style={{ margin: 0, font: 'inherit' }}>
                    {e.body}
                  </pre>
                </section>
              )
            }
            if (e.kind === 'notice') {
              // Neutral client-side notice (e.g. a mistyped command). Nothing ran,
              // so it gets NO run-failure badge and NO "— not a verdict" suffix —
              // just a dim line, the same muted treatment as the .meta canary label.
              return (
                <p key={e.id} className="meta">
                  {e.text}
                </p>
              )
            }
            if (e.kind === 'input') {
              return (
                <div key={e.id} className="echo">
                  <p className="cmd">
                    <span className="p" aria-hidden="true">
                      ❯
                    </span>
                    {e.text}
                  </p>
                  <span className="stamp">#{e.id}</span>
                </div>
              )
            }
            if (e.kind === 'verdict') {
              const v = VERDICT_META[e.run.verdict]
              // Prefer structured steps[] when the run carries them; else fall
              // back to the flat human_trace (PROVEN-only). Captured as consts so
              // any narrowing survives inside the .map callbacks below.
              const steps = e.run.steps ?? null
              const trace =
                e.run.verdict === 'PROVEN' ? e.run.human_trace : null
              // Structured-trace summary bits (only consumed when steps render).
              const decidedIdx = steps ? steps.findIndex((s) => s.decided) : -1
              const stopped = steps
                ? steps.some((s) => s.status === 'skipped')
                : false
              return (
                <div key={e.id} className={`result ${v.cls}`}>
                  <p className="verdict">
                    <span className="chip">
                      <span aria-hidden="true">{v.glyph} </span>
                      {v.label}
                    </span>
                    {e.note && <span>{e.note}</span>}
                  </p>
                  {/* Canary token — surfaced verbatim as the run's evidence.
                      Rendered on any verdict (PROVEN / NOT PROVEN); never on the
                      RUN FAILED branch, which is a separate return below. */}
                  {e.run.canary && (
                    <p className="meta">
                      canary{' '}
                      <span className="canary-token">{e.run.canary}</span>
                    </p>
                  )}
                  {steps && steps.length > 0 ? (
                    <details
                      className="trace"
                      {...(idx === entries.length - 1 ? { open: true } : {})}
                    >
                      <summary>
                        trace · {steps.length} step
                        {steps.length === 1 ? '' : 's'}
                        {decidedIdx >= 0
                          ? ` · ${stopped ? 'stopped' : 'decided'} at step ${decidedIdx + 1}`
                          : ''}
                      </summary>
                      <ol className="steps">
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
                      {...(idx === entries.length - 1 ? { open: true } : {})}
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
                </div>
              )
            }
            // kind === 'error' — a RUN FAILED is NOT a verdict: dashed rail +
            // outlined chip set it apart from PROVEN / NOT PROVEN.
            return (
              <div key={e.id} className="result is-fail">
                <p className="verdict">
                  <span className="chip chip-outline">
                    <span aria-hidden="true">! </span>RUN FAILED
                  </span>
                  <span>{e.message} — not a verdict</span>
                </p>
              </div>
            )
          })}

          {/* Running — honest subset: CSS quadrant spinner + a rotating music
              verb (step-agnostic, route B) + live elapsed. No step counter / no
              fake steps (no live step data). Dim rail (no is-* class). */}
          {verifying && (
            <div className="result" aria-busy="true">
              <p className="verdict">
                <span aria-hidden="true">
                  <span className="spin-clover" aria-hidden="true">
                    <i className="cd cd1" />
                    <i className="cd cd2" />
                    <i className="cd cd3" />
                    <i className="cd cd4" />
                  </span>
                  <Verb text={runVerb} />
                </span>
                <span className="dim stats">
                  {elapsedLabel}
                  {isFirstRun ? ' · cold start ~12s' : ''}
                </span>
                <span className="sr-only">Verifying — {elapsedLabel} elapsed</span>
              </p>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </section>

      {/* ROW 3 — prompt: pinned under the transcript, full width */}
      <div className="prompt">
        <label className="sr-only" htmlFor="q">
          Input to verify
        </label>
        <form className="prompt-box" onSubmit={onSubmit}>
          <span className="p" aria-hidden="true">
            ❯
          </span>
          {/* native-caret only for wide chars (emoji/CJK), where a per-cell block
              can't track the caret — then the native green caret shows and .cursor
              hides (CSS). For normal ASCII the block cursor shows, native hidden. */}
          <div
            className={`field${WIDE_CHARS.test(input) ? ' native-caret' : ''}`}
          >
            <input
              id="q"
              ref={inputRef}
              type="text"
              value={input}
              onChange={(ev) => {
                setInput(ev.target.value)
                setHistIdx(null) // typing exits history mode, back to a live draft
              }}
              onKeyDown={onKeyDown}
              onKeyUp={place}
              onClick={place}
              onScroll={place}
              onSelect={place}
              maxLength={2000}
              disabled={verifying}
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              enterKeyHint="go"
              placeholder="paste an input to verify"
            />
            <span className="cursor" ref={cursorRef} aria-hidden="true" />
          </div>
          <button
            type="submit"
            className={`go${input.trim() !== '' && !verifying ? ' is-ready' : ''}`}
            disabled={verifying || input.trim() === ''}
          >
            {verifying ? 'verifying…' : '⏎ verify'}
          </button>
        </form>
        {/* Prompt hint (HANDOFF §5 p.hint). Both items are real behavior: ⏎ submits
            the form (onSubmit); ↑/↓ walk submitted-input history (in-memory, this
            session). esc is still not built, so it stays omitted — the hint states
            only true behavior. */}
        <p className="hint">
          <kbd>⏎</kbd> verify · <kbd>↑</kbd> history · /help
        </p>
      </div>

      {/* ROW 4 — eval-ledger footer */}
      <footer className="status">
        <ul aria-label="Eval ledger">{ledger}</ul>
      </footer>
    </>
  )
}

export default Verify
