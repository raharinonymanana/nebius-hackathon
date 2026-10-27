import type { Run } from './contract'

export type Entry =
  | { id: number; kind: 'banner' }
  | { id: number; kind: 'input'; text: string }
  | { id: number; kind: 'verdict'; run: Run; note: string | null }
  | { id: number; kind: 'error'; message: string }
  | { id: number; kind: 'help' }
  | { id: number; kind: 'notice'; text: string }
  | { id: number; kind: 'output'; title: string; body: string }

// Transcript persistence (sessionStorage — per-tab, cleared when the tab closes).
// Only `entries` is persisted; every other piece of state stays transient. The key
// is versioned so a future shape change can invalidate old data cleanly.
export const TRANSCRIPT_KEY = 'melodie.transcript.v1'
export const DEFAULT_ENTRIES: Entry[] = [{ id: 0, kind: 'banner' }]

// Lazy initializer for `entries`. Reads sessionStorage defensively: any parse error,
// wrong shape, or empty array falls back to the banner-only default, and a corrupt
// value is dropped so it can't wedge every future load. Never throws (storage access
// itself can throw in private-mode / blocked-cookie contexts).
export function loadEntries(): Entry[] {
  try {
    const raw = sessionStorage.getItem(TRANSCRIPT_KEY)
    if (!raw) return DEFAULT_ENTRIES
    const parsed = JSON.parse(raw)
    const ok =
      Array.isArray(parsed) &&
      parsed.length > 0 &&
      parsed.every(
        (e) => e && typeof e.id === 'number' && typeof e.kind === 'string',
      )
    if (!ok) {
      sessionStorage.removeItem(TRANSCRIPT_KEY)
      return DEFAULT_ENTRIES
    }
    return parsed as Entry[]
  } catch {
    return DEFAULT_ENTRIES
  }
}

// The title-bar tally's definition of a run: a landed PROVEN / NOT PROVEN verdict.
// A RUN FAILED (kind 'error') is neither ✓ nor ✗ and FIX VERIFIED is not a tally
// bucket, so neither counts. Shared by the tally and runStamps so the two can't drift.
export function isTalliedRun(e: Entry): boolean {
  return (
    e.kind === 'verdict' &&
    (e.run.verdict === 'PROVEN' || e.run.verdict === 'NOT PROVEN')
  )
}

// Run-number stamps, DERIVED from entries (never stored): input entry id → its
// ordinal among tallied runs. Each outcome entry pairs with the input just before
// it; only an input whose outcome isTalliedRun gets a number, so slash commands,
// RUN FAILED and FIX VERIFIED echoes carry none. While `inFlight`, a trailing
// input with no outcome yet is stamped with the next number (= what RUNNING #n
// shows). Survives a sessionStorage restore unchanged; /clear restarts at #1.
export function runStamps(entries: Entry[], inFlight: boolean): Map<number, number> {
  const stamps = new Map<number, number>()
  let n = 0
  let pending: number | null = null // id of the input awaiting its outcome
  for (const e of entries) {
    if (e.kind === 'input') {
      pending = e.id
    } else if (pending !== null) {
      if (isTalliedRun(e)) stamps.set(pending, ++n)
      pending = null
    }
  }
  if (inFlight && pending !== null) stamps.set(pending, n + 1)
  return stamps
}
