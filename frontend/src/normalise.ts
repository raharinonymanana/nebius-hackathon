import type { Contract } from './contract'

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
