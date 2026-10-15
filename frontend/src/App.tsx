import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Contract } from './contract'
import { normalise } from './normalise'
import Verify from './Verify'
import MelodieMark from './MelodieMark'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; contract: Contract }

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })
  // Portal host for the live title-bar status. The tally + mode are DERIVED and
  // rendered by Verify (where entries/verifying live); App only lends the slot.
  // This useState holds a DOM handle, not the tally — the tally is never stored.
  const [statusSlot, setStatusSlot] = useState<HTMLSpanElement | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/data')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((raw) => normalise(raw))
      .then((contract) => {
        if (!cancelled) setState({ status: 'loaded', contract })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err)
          setState({ status: 'error', message })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Eval ledger (status line, row 3). These are the ENGINE/eval numbers, not the
  // live replay path — labels --dim, numbers --fg, money fixed to 2dp (no raw float).
  let ledger: ReactNode
  if (state.status === 'loading') {
    ledger = (
      <>
        eval ledger · <span className="led-dim">loading…</span>
      </>
    )
  } else if (state.status === 'error') {
    ledger = (
      <>
        eval ledger · <span className="led-dim">unavailable</span>
      </>
    )
  } else {
    const { meta } = state.contract
    ledger = (
      <>
        eval ledger · receipts <span className="led-n">{meta.receipts_valid}</span> (+
        <span className="led-n">{meta.receipts_excluded}</span> excl) · calls{' '}
        <span className="led-n">{meta.model_calls}</span> ·{' '}
        <span className="led-n">${meta.model_cost_usd.toFixed(2)}</span> · tavily{' '}
        <span className="led-n">{meta.tavily_credits}</span>
      </>
    )
  }

  return (
    <div className="pane">
      <header className="titlebar">
        <MelodieMark size={22} />
        <span className="wordmark">mélodie</span>
        <span className="tt-status" ref={setStatusSlot} />
      </header>
      <Verify ledger={ledger} statusSlot={statusSlot} />
    </div>
  )
}

export default App
