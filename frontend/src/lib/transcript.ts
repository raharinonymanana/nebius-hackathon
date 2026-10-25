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
