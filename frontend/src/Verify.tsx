import { useState } from 'react'
import type { Run } from './contract'
import { normaliseRun } from './normalise'

const TARGET = 'ormar'
// Backend budget is ~25s (cold start ~12s). Give the browser headroom above that
// so the backend's own graceful NOT-PROVEN reply wins over a client-side abort.
const TIMEOUT_MS = 30000

type VerifyState =
  | { status: 'idle' }
  | { status: 'verifying' }
  | { status: 'done'; run: Run; note: string | null }
  | { status: 'error'; message: string }

function Verify() {
  const [input, setInput] = useState('')
  const [state, setState] = useState<VerifyState>({ status: 'idle' })

  async function onVerify() {
    setState({ status: 'verifying' })
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
    try {
      const res = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: TARGET, input }),
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
      setState({ status: 'done', run, note })
    } catch (err: unknown) {
      const message =
        err instanceof DOMException && err.name === 'AbortError'
          ? `timed out after ${TIMEOUT_MS / 1000}s`
          : err instanceof Error
            ? err.message
            : String(err)
      setState({ status: 'error', message })
    } finally {
      clearTimeout(timer)
    }
  }

  return (
    <div>
      <h2>live verify (target: {TARGET})</h2>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="exploit input string"
        disabled={state.status === 'verifying'}
      />
      <button
        onClick={onVerify}
        disabled={state.status === 'verifying' || input === ''}
      >
        Verify
      </button>

      {state.status === 'verifying' && (
        <p>verifying… (cold start can take ~12s)</p>
      )}

      {state.status === 'error' && <p>error: {state.message}</p>}

      {state.status === 'done' && (
        <div>
          <p>verdict: {state.run.verdict}</p>
          {state.note !== null && <p>note: {state.note}</p>}
          {state.run.verdict === 'PROVEN' && (
            <div>
              <p>human_trace:</p>
              <pre>{state.run.human_trace.join('\n')}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Verify
