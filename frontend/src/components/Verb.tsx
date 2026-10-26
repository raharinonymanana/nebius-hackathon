import { useGlint, usePrefersReducedMotion } from '../hooks/terminal-hooks'

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
