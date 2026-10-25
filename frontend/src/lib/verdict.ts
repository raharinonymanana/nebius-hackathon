import type { Run } from './contract'

// Verdict presentation, keyed on the exact contract literals (Run['verdict']).
// Colour is never the sole signal: each chip carries a glyph + text label. The
// class is the RESULT class (sets --rail); the chip itself is just .chip.
// FIX VERIFIED is dead in the live verify flow (the backend returns only
// PROVEN / NOT PROVEN); its entry stays only to satisfy the Record type.
export const VERDICT_META: Record<
  Run['verdict'],
  { label: string; glyph: string; cls: string }
> = {
  PROVEN: { label: 'PROVEN', glyph: '✓', cls: 'is-proven' },
  'NOT PROVEN': { label: 'NOT PROVEN', glyph: '✗', cls: 'is-not-proven' },
  'FIX VERIFIED': { label: 'FIX VERIFIED', glyph: '◆', cls: 'is-proven' },
}
