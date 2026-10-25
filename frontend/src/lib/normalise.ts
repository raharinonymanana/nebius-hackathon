import type { Contract, Run } from './contract'

// The ONLY place raw JSON from the backend is touched.
// Step 1: assert the top-level shape and return it typed. No rendering logic.
// Throws a named Error if a required top-level key is missing.
export function normalise(raw: unknown): Contract {
  if (raw === null || typeof raw !== 'object') {
    throw new Error('contract is not an object')
  }

  const obj = raw as Record<string, unknown>
  const required = [
    'schema_version',
    'generated_utc',
    'meta',
    'targets',
    'eval',
  ]
  for (const key of required) {
    if (!(key in obj)) {
      throw new Error(`contract missing required key: ${key}`)
    }
  }

  return obj as unknown as Contract
}

// The verify lane: POST /api/verify returns a single Run, NOT a Contract.
// Same house style as normalise(): check the one discriminant that matters
// (verdict — the field every honesty guarantee hangs on), then cast. Throws a named Error otherwise.
const VERDICTS = ['PROVEN', 'NOT PROVEN', 'FIX VERIFIED'] as const

export function normaliseRun(raw: unknown): Run {
  if (raw === null || typeof raw !== 'object') {
    throw new Error('run is not an object')
  }
  const obj = raw as Record<string, unknown>
  const verdict = obj.verdict
  if (
    typeof verdict !== 'string' ||
    !(VERDICTS as readonly string[]).includes(verdict)
  ) {
    throw new Error(`run has invalid verdict: ${String(verdict)}`)
  }
  return obj as unknown as Run
}
