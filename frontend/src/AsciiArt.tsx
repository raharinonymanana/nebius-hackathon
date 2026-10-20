import type { CSSProperties } from 'react'
import type { AsciiPiece } from './melodie-art'

// Decorative monospace art renderer. Walks art/fg/bg together, one cell at a
// time, and emits a styled <span> wherever a tone is present — fg tone → glyph
// colour, bg tone → cell background (a half-block cell can carry both, which is
// how the gradient steps every half-row). Cells with no tone stay literal text
// so every column aligns. The whole block is aria-hidden (purely visual).
const TONE: Record<string, string> = {
  '1': 'var(--mk-1)',
  '2': 'var(--mk-2)',
  '3': 'var(--mk-3)',
  '4': 'var(--mk-4)',
  '5': 'var(--mk-5)',
}

const PRE: CSSProperties = { font: 'inherit', whiteSpace: 'pre', margin: 0 }

export function AsciiArt({ piece }: { piece: AsciiPiece }) {
  const { art, fg, bg } = piece
  return (
    <pre style={PRE} aria-hidden="true">
      {art.map((row, r) => {
        const cells = Array.from(row).map((ch, c) => {
          const color = TONE[fg[r]?.[c] ?? '']
          const background = TONE[bg[r]?.[c] ?? '']
          // No tone either side → keep the character literal (preserves columns).
          if (!color && !background) return ch
          return (
            <span key={c} style={{ color, background }}>
              {ch}
            </span>
          )
        })
        // Keep each source row on its own line (last row gets no trailing \n).
        return (
          <span key={r}>
            {cells}
            {r < art.length - 1 ? '\n' : ''}
          </span>
        )
      })}
    </pre>
  )
}
