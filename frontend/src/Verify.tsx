import { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'
import type { Run, Contract } from './lib/contract'
import { normaliseRun } from './lib/normalise'
import { TARGET, TIMEOUT_MS } from './lib/config'
import type { Entry } from './lib/transcript'
import { TRANSCRIPT_KEY, loadEntries, isTalliedRun, runStamps } from './lib/transcript'
import { buildCommand, DATA_COMMANDS } from './lib/commands'
import { useBlockCursor, useRotatingVerb, useRotatingConcept } from './hooks/terminal-hooks'
import { TitleStatus } from './components/TitleStatus'
import { AboutBox } from './components/AboutBox'
import { EchoRow } from './components/EchoRow'
import { HelpBox, OutputBox } from './components/CommandBox'
import { RunResult, RunFailed } from './components/RunResult'
import { RunningBlock } from './components/RunningBlock'
import { PromptRow } from './components/PromptRow'

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
  // Block cursor: owns the input ref + the sibling .cursor ref, and
  // positions the block at caret index × 1ch. inputRef also serves the focus effect.
  const { inputRef, cursorRef, place } = useBlockCursor(input)
  // Running-state verb: rotates every 3s through step-agnostic phrases while a
  // verify is in flight (honours reduced-motion internally). Keyed on the real
  // in-flight boolean; the hook takes no step param, so it can't name a phase.
  const runVerb = useRotatingVerb(verifying)
  // Running-state concept rail: one true mechanism fact, cycled in order every
  // 4.5s while in flight (offset from the verb). Same honesty basis as the verb
  // — describes the harness, never a live step; honours reduced-motion inside.
  const runConcept = useRotatingConcept(verifying)
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
    const input = inputRef.current
    if (!verifying) input?.focus()
  }, [verifying, inputRef])

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
  }, [histIdx, place, inputRef])

  // Live elapsed timer for the in-flight spinner. Ephemeral UI state ONLY — it
  // never touches entries / idRef / the append-only log. Ticks ~10x/s while a
  // verify is in flight; a number updating is not vestibular motion, so it keeps
  // ticking under prefers-reduced-motion (only the spinner glyph freezes, via CSS).
  useEffect(() => {
    if (!verifying) return
    const start = Date.now()
    // oxlint-disable-next-line react/set-state-in-effect -- intentional reset of the ephemeral elapsed timer when a run starts
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
      } else if ((DATA_COMMANDS as readonly string[]).includes(name)) {
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
  // NOT folded into "runs"; it gets its own "! n" bucket (a crash is never counted as a verdict). FIX VERIFIED is
  // intentionally not a tally bucket.
  const proven = entries.filter(
    (e) => e.kind === 'verdict' && e.run.verdict === 'PROVEN',
  ).length
  const notProven = entries.filter(
    (e) => e.kind === 'verdict' && e.run.verdict === 'NOT PROVEN',
  ).length
  const failed = entries.filter((e) => e.kind === 'error').length
  const runs = entries.filter(isTalliedRun).length // = proven + notProven
  // Echo stamps are run ordinals under the SAME rule (runStamps → isTalliedRun),
  // not entry ids. While a verify is in flight the mode shows the number its echo
  // carries — the next run number — rendered as the same bare #{n}.
  const stamps = runStamps(entries, verifying)
  const inFlightRun = runs + 1
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
          <TitleStatus
            runs={runs}
            proven={proven}
            notProven={notProven}
            failed={failed}
            verifying={verifying}
            inFlightRun={inFlightRun}
          />,
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
              return (
                <AboutBox
                  key={e.id}
                  contract={contract}
                  verifying={verifying}
                  runLive={runLive}
                  runReplay={runReplay}
                />
              )
            }
            if (e.kind === 'help') {
              return <HelpBox key={e.id} id={e.id} />
            }
            if (e.kind === 'output') {
              return <OutputBox key={e.id} id={e.id} title={e.title} body={e.body} />
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
              return <EchoRow key={e.id} n={stamps.get(e.id)} text={e.text} />
            }
            if (e.kind === 'verdict') {
              return (
                <RunResult
                  key={e.id}
                  run={e.run}
                  note={e.note}
                  isLatest={idx === entries.length - 1}
                />
              )
            }
            // kind === 'error' — a RUN FAILED is NOT a verdict: dashed rail +
            // outlined chip set it apart from PROVEN / NOT PROVEN.
            return <RunFailed key={e.id} message={e.message} />
          })}

          {/* Running — the verb (step-agnostic music flavour) stays on
              the spinner line, unchanged. Below it: a STATIC pipeline (the fixed
              six stages, all dimmed, no marks — a description of what the harness
              does, never a claim about which stage is live) and a rotating concept
              rail (one true mechanism fact). Dim rail (no is-* class). The real
              steps[] reveal replaces the pipeline the instant the run lands. All
              enrichment is aria-hidden; the sr-only line stays the SR truth. */}
          {verifying && (
            <RunningBlock
              verb={runVerb}
              concept={runConcept}
              elapsedLabel={elapsedLabel}
              isFirstRun={isFirstRun}
            />
          )}

          <div ref={bottomRef} />
        </div>
      </section>

      {/* ROW 3 — prompt: pinned under the transcript, full width */}
      <PromptRow
        input={input}
        verifying={verifying}
        onChange={(ev) => {
          setInput(ev.target.value)
          setHistIdx(null) // typing exits history mode, back to a live draft
        }}
        onKeyDown={onKeyDown}
        onSubmit={onSubmit}
        inputRef={inputRef}
        cursorRef={cursorRef}
        place={place}
      />

      {/* ROW 4 — eval-ledger footer */}
      <footer className="status">
        <ul aria-label="Eval ledger">{ledger}</ul>
      </footer>
    </>
  )
}

export default Verify
