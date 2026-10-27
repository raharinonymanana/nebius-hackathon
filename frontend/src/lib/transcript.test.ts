import { describe, it, expect } from 'vitest'
import type { Run } from './contract'
import type { Entry } from './transcript'
import { isTalliedRun, runStamps } from './transcript'

// Minimal fixtures — runStamps / isTalliedRun read only kind and run.verdict.
const run = (verdict: string) => ({ verdict }) as unknown as Run
const banner: Entry = { id: 0, kind: 'banner' }
const input = (id: number, text = 'x'): Entry => ({ id, kind: 'input', text })
const verdict = (id: number, v = 'PROVEN'): Entry => ({ id, kind: 'verdict', run: run(v), note: null })
const failed = (id: number): Entry => ({ id, kind: 'error', message: 'HTTP 502' })

// The title-bar tally's run total, as Verify derives it.
const tally = (entries: Entry[]) => entries.filter(isTalliedRun).length

describe('runStamps', () => {
  it('stamps two consecutive runs 1, 2 (not their entry ids 1, 3)', () => {
    const entries = [banner, input(1), verdict(2), input(3), verdict(4, 'NOT PROVEN')]
    const s = runStamps(entries, false)
    expect(s.get(1)).toBe(1)
    expect(s.get(3)).toBe(2)
    expect(s.size).toBe(tally(entries))
  })

  it('skips a /help echo: run, /help, run → 1, 2 with no number on /help', () => {
    const entries: Entry[] = [
      banner,
      input(1), verdict(2),
      input(3, '/help'), { id: 4, kind: 'help' },
      input(5), verdict(6),
    ]
    const s = runStamps(entries, false)
    expect(s.get(1)).toBe(1)
    expect(s.has(3)).toBe(false)
    expect(s.get(5)).toBe(2)
  })

  it('counts a RUN FAILED iff the tally does (it does not) — no number, next run unshifted', () => {
    const entries = [banner, input(1), failed(2), input(3), verdict(4)]
    const s = runStamps(entries, false)
    expect(tally(entries)).toBe(1)
    expect(s.has(1)).toBe(false)
    expect(s.get(3)).toBe(1)
    expect(s.size).toBe(tally(entries))
  })

  it('restarts at 1 after a /clear-style reset (fresh banner + id sequence)', () => {
    const before = [banner, input(1), verdict(2), input(3), verdict(4)]
    expect(runStamps(before, false).get(3)).toBe(2)
    const after = [banner, input(1), verdict(2)]
    expect(runStamps(after, false).get(1)).toBe(1)
  })

  it('stamps the in-flight input with the next number (what RUNNING #n shows)', () => {
    const entries = [banner, input(1), verdict(2), input(3)]
    expect(runStamps(entries, true).get(3)).toBe(tally(entries) + 1)
    expect(runStamps(entries, false).has(3)).toBe(false) // orphaned after a reload mid-run
  })
})
