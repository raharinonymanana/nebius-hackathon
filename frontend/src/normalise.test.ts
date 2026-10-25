import { describe, it, expect } from 'vitest'
import { normalise, normaliseRun } from './normalise'

// Minimal object carrying every key normalise() requires.
const validContract = {
  schema_version: 1,
  generated_utc: '2026-10-25T00:00:00+00:00',
  meta: {},
  targets: [],
  eval: {},
}

describe('normalise (contract top-level shape guard)', () => {
  it('returns the object unchanged when all required keys are present', () => {
    expect(normalise(validContract)).toBe(validContract)
  })

  it('throws on null or a non-object', () => {
    expect(() => normalise(null)).toThrow('contract is not an object')
    expect(() => normalise(42)).toThrow('contract is not an object')
    expect(() => normalise('nope')).toThrow('contract is not an object')
  })

  it('names the missing required key', () => {
    for (const key of ['schema_version', 'generated_utc', 'meta', 'targets', 'eval']) {
      const partial = { ...validContract } as Record<string, unknown>
      delete partial[key]
      expect(() => normalise(partial)).toThrow(`contract missing required key: ${key}`)
    }
  })
})

describe('normaliseRun (verdict discriminant guard -- the field every honesty guarantee hangs on)', () => {
  it('accepts each of the three contract verdicts', () => {
    for (const verdict of ['PROVEN', 'NOT PROVEN', 'FIX VERIFIED']) {
      expect(normaliseRun({ verdict })).toEqual({ verdict })
    }
  })

  it('throws on null or a non-object', () => {
    expect(() => normaliseRun(null)).toThrow('run is not an object')
    expect(() => normaliseRun(7)).toThrow('run is not an object')
  })

  it('throws on a missing or unknown verdict (never silently trusts the backend)', () => {
    expect(() => normaliseRun({})).toThrow('run has invalid verdict: undefined')
    expect(() => normaliseRun({ verdict: 'MAYBE' })).toThrow('run has invalid verdict: MAYBE')
    expect(() => normaliseRun({ verdict: 123 })).toThrow('run has invalid verdict: 123')
    // guard against a lowercased spoof slipping through
    expect(() => normaliseRun({ verdict: 'proven' })).toThrow('run has invalid verdict: proven')
  })
})
