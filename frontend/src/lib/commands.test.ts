import { describe, it, expect } from 'vitest'
import type { Contract } from './contract'
import { evalRate, buildCommand, classesBody, SCOPE_BODY } from './commands'

// Minimal fixtures typed `as unknown as Contract` — only the fields each function
// reads are supplied. TARGET is 'ormar' (lib/config), which classesBody keys on.

// evalRate reads only c.eval, and within it only the rate rows.
function makeEval(rows: unknown[]): Contract['eval'] {
  return { rows, remediation: [], notes: [] } as unknown as Contract['eval']
}

describe('evalRate', () => {
  it('returns the weaponise rate string when a matching rate row has ci_lo !== null', () => {
    const ev = makeEval([
      { kind: 'rate', target: 'ormar', axis: 'weaponise pass@1', ci_lo: 0.1, rate_str: '3/5', ci_str: '95% CI' },
    ])
    expect(evalRate(ev, 'ormar-aggregate')).toBe('weaponise 3/5 95% CI')
  })

  it("falls back to 'locate' when no weaponise row matches", () => {
    const ev = makeEval([
      { kind: 'rate', target: 'ormar', axis: 'locate pass@1', ci_lo: 0.2, rate_str: '4/5', ci_str: '90% CI' },
    ])
    expect(evalRate(ev, 'ormar-aggregate')).toBe('locate 4/5 90% CI')
  })

  it('returns null when the only matching row has ci_lo === null', () => {
    const ev = makeEval([
      { kind: 'rate', target: 'ormar', axis: 'weaponise pass@1', ci_lo: null, rate_str: '3/5', ci_str: '' },
    ])
    expect(evalRate(ev, 'ormar-aggregate')).toBeNull()
  })

  it('returns null when the target has no rows', () => {
    expect(evalRate(makeEval([]), 'ormar-aggregate')).toBeNull()
  })
})

describe('buildCommand', () => {
  const c = {} as unknown as Contract

  it("'scope' body is SCOPE_BODY verbatim", () => {
    expect(buildCommand('scope', c).body).toBe(SCOPE_BODY)
  })

  it('an unknown command returns { title: name, body: "" }', () => {
    expect(buildCommand('nope', c)).toEqual({ title: 'nope', body: '' })
  })
})

describe('classesBody', () => {
  it('marks the TARGET-prefixed target [LIVE] and every other [REPLAY]', () => {
    const c = {
      targets: [
        { id: 'ormar-aggregate', cve: 'CVE-ORMAR', exploit_class: 'SQL injection', vulnerable_version: '1', fixed_version: '2' },
        { id: 'starlette-static', cve: 'CVE-STAR', exploit_class: 'path traversal', vulnerable_version: '3', fixed_version: '4' },
      ],
      eval: { rows: [], remediation: [], notes: [] },
    } as unknown as Contract
    const body = classesBody(c)
    expect(body).toContain('CVE-ORMAR  [LIVE]')
    expect(body).toContain('CVE-STAR  [REPLAY]')
  })
})
