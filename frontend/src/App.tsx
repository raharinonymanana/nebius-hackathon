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

  // Eval ledger (status footer, row 4) — the ENGINE/eval numbers, not the live
  // replay path. Rendered as <li> items (Verify wraps them in <footer.status><ul>).
  // Numbers in --fg via .n; money fixed to 2dp (no raw float). Lower-priority
  // items carry .wide so the ≤640px rule can drop them.
  let ledger: ReactNode
  if (state.status === 'loading') {
    ledger = <li className="dim">eval ledger · loading…</li>
  } else if (state.status === 'error') {
    ledger = <li className="dim">eval ledger · unavailable</li>
  } else {
    const { meta } = state.contract
    ledger = (
      <>
        <li>
          receipts <span className="n">{meta.receipts_valid}</span>
          <span className="wide"> (+{meta.receipts_excluded} excluded)</span>
        </li>
        <li className="wide">
          model calls <span className="n">{meta.model_calls}</span>
        </li>
        <li>
          cost <span className="n">${meta.model_cost_usd.toFixed(2)}</span>
        </li>
        <li className="wide">
          tavily credits <span className="n">{meta.tavily_credits}</span>
        </li>
      </>
    )
  }

  return (
    <div className="term">
      <header className="top">
        <span className="rule end" aria-hidden="true" />
        <MelodieMark size={16} />
        <h1>mélodie</h1>
        <span className="rule" aria-hidden="true" />
        {/* Title-bar status slot — portal host. display:contents so the tally +
            mode Verify portals in here become direct flex children of .top (the
            1ch gap + the flexible .rule before them lay them out exactly as v3). */}
        <span ref={setStatusSlot} style={{ display: 'contents' }} />
        <span className="rule end" aria-hidden="true" />
      </header>
      <Verify ledger={ledger} statusSlot={statusSlot} contract={state.status === 'loaded' ? state.contract : null} />
    </div>
  )
}

export default App
