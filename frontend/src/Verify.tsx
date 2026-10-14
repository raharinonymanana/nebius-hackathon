import { useState, useRef, useEffect, useLayoutEffect } from 'react'
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

function Verify() {
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
    bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' })
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
    <div>
      {entries.map((e) => (
        <div key={e.id}>
          {e.kind === 'banner' && <pre className="entry-banner">{BANNER}</pre>}
          {e.kind === 'input' && <div className="entry-input">❯ {e.text}</div>}
          {e.kind === 'verdict' && (
            <div className="entry-verdict">
              <div>{e.run.verdict}</div>
              {e.note && <div>{e.note}</div>}
              {e.run.verdict === 'PROVEN' && (
                <pre className="entry-trace">{e.run.human_trace.join('\n')}</pre>
              )}
            </div>
          )}
          {e.kind === 'error' && (
            <div className="entry-error">error: {e.message}</div>
          )}
        </div>
      ))}

      {verifying && (
        <div className="verifying-line">verifying… (cold start ~12s)</div>
      )}

      <form className="prompt-form" onSubmit={onSubmit}>
        <input
          ref={inputRef}
          className="prompt-input"
          value={input}
          onChange={(ev) => setInput(ev.target.value)}
          maxLength={2000}
          disabled={verifying}
          autoComplete="off"
          spellCheck={false}
        />
        <button type="submit" disabled={verifying || input.trim() === ''}>
          verify
        </button>
      </form>

      <div ref={bottomRef} />
    </div>
  )
}

export default Verify
