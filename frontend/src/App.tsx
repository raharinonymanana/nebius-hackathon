import { useEffect, useState } from 'react'
import type { Contract } from './contract'
import { normalise } from './normalise'

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

  if (state.status === 'loading') {
    return <p>loading contract…</p>
  }

  if (state.status === 'error') {
    return <p>error: {state.message}</p>
  }

  const { meta } = state.contract
  return (
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

export default App
