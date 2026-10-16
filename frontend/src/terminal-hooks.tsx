// Terminal UI hooks — copied from design/melodie-HANDOFF-v3.md §9, as written.
// Scope: presentation/behaviour only (block cursor, reduced-motion, verb glint).
// useStepVerb / verb ROTATION are intentionally NOT ported: there is no live
// step data yet, so the running verb stays a single static string and only
// glints. (Rotation is deferred to the structured-trace backend session.)

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
