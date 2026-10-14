import { useEffect, useState } from 'react'
import type { Contract } from './contract'
import { normalise } from './normalise'
import Verify from './Verify'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; contract: Contract }

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })

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

  let metaView
  if (state.status === 'loading') {
    metaView = <p>loading contract…</p>
  } else if (state.status === 'error') {
    metaView = <p>error: {state.message}</p>
  } else {
    const { meta } = state.contract
    metaView = (
      <div>
        <div>model cost: ${meta.model_cost_usd}</div>
        <div>model calls: {meta.model_calls}</div>
        <div>
          valid receipts: {meta.receipts_valid} (+{meta.receipts_excluded} excluded)
        </div>
        <div>tavily credits: {meta.tavily_credits}</div>
      </div>
    )
  }

  return (
    <div>
      <Verify />
      {metaView}
    </div>
  )
}

export default App
