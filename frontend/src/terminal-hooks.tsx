// Terminal UI hooks — copied from design/melodie-HANDOFF-v3.md §9, as written.
// Scope: presentation/behaviour only (block cursor, reduced-motion, verb glint).
// useStepVerb is intentionally NOT ported: there is no live step data, so the
// running verb never names a phase. The verb DOES rotate (useRotatingVerb,
// route B / decorative) through step-agnostic phrases — it takes no step param.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

export const WIDE_CHARS = /[ᄀ-ᅟ⺀-￿]|[\uD800-\uDFFF]/ // emoji/CJK → native caret

export function useBlockCursor(value: string) {
  const inputRef = useRef<HTMLInputElement>(null)
  const cursorRef = useRef<HTMLSpanElement>(null)

  const place = useCallback(() => {
    const input = inputRef.current
    const cursor = cursorRef.current
    if (!input || !cursor) return
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? start
    const pos = input.selectionDirection === 'backward' ? start : end
    const cell = cursor.getBoundingClientRect().width // sub-pixel 1ch (offsetWidth rounds → drift)
    cursor.style.transform = `translateX(${pos * cell - input.scrollLeft}px)`
    cursor.hidden = start !== end // a selection shows the native highlight instead
  }, [])

  useLayoutEffect(place, [value, place])
  useEffect(() => {
    const onSelection = () => {
      if (document.activeElement === inputRef.current) place()
    }
    document.addEventListener('selectionchange', onSelection)
    window.addEventListener('resize', place)
    void document.fonts.ready.then(place) // 1ch changes once the font loads
    return () => {
      document.removeEventListener('selectionchange', onSelection)
      window.removeEventListener('resize', place)
    }
  }, [place])

  return { inputRef, cursorRef, place }
}

export function usePrefersReducedMotion(): boolean {
  const q = '(prefers-reduced-motion: reduce)'
  const [reduce, setReduce] = useState(() => window.matchMedia(q).matches)
  useEffect(() => {
    const mq = window.matchMedia(q)
    const onChange = () => setReduce(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return reduce
}

/** Index of the 3-cell glint (−3 = off). One cell per 80 ms, short pause between sweeps. */
export function useGlint(length: number, enabled: boolean): number {
  const [at, setAt] = useState(-3)
  useEffect(() => {
    setAt(-3)
    if (!enabled) return
    const id = window.setInterval(() => setAt((n) => (n > length + 12 ? -3 : n + 1)), 80)
    return () => window.clearInterval(id)
  }, [length, enabled])
  return at
}

// Step-AGNOSTIC botanic / flower / music words for the running state. None names
// or implies an observable internal step, and none implies invention — a run
// really is in flight, so a decorative label is honest; naming a phase is not.
const ROTATING_VERBS = [
  'Blooming', 'Flourishing', 'Budding', 'Blossoming', 'Unfurling', 'Greening',
  'Crescendo', 'Harmonizing', 'Resonating', 'Humming', 'Lilting', 'Trilling',
  'Petalfall', 'Tendril', 'Grace-note', 'Wildflower',
  'Verdant', 'Florid', 'Cadence', 'Songbird',
]

/** The running verb, rotated every 3s through step-agnostic phrases (route B,
 * decorative). Takes NO step param by construction — it cannot name a phase.
 * Reduced-motion or not-running: a single stable phrase, no interval. */
export function useRotatingVerb(running: boolean): string {
  const reduce = usePrefersReducedMotion()
  const [verb, setVerb] = useState(
    () => ROTATING_VERBS[Math.floor(Math.random() * ROTATING_VERBS.length)],
  )
  useEffect(() => {
    if (!running || reduce) return
    const id = window.setInterval(() => {
      setVerb((prev) => {
        let next = prev
        while (next === prev) {
          next = ROTATING_VERBS[Math.floor(Math.random() * ROTATING_VERBS.length)]
        }
        return next // never the same twice in a row
      })
    }, 3000)
    return () => window.clearInterval(id)
  }, [running, reduce])
  return verb
}

export function Verb({ text }: { text: string }) {
  const reduce = usePrefersReducedMotion()
  const chars = Array.from(text + '…')
  const at = useGlint(chars.length, !reduce)
  return (
    <span className="verb">
      {chars.map((c, i) => (
        <span key={i} className={i >= at && i < at + 3 ? 'hi' : undefined}>
          {c}
        </span>
      ))}
    </span>
  )
}
