import { WIDE_CHARS } from '../hooks/terminal-hooks'

export function PromptRow({
  input,
  verifying,
  onChange,
  onKeyDown,
  onSubmit,
  inputRef,
  cursorRef,
  place,
}: {
  input: string
  verifying: boolean
  onChange: (ev: React.ChangeEvent<HTMLInputElement>) => void
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void
  onSubmit: (e: React.FormEvent) => void
  inputRef: React.RefObject<HTMLInputElement | null>
  cursorRef: React.RefObject<HTMLSpanElement | null>
  place: () => void
}) {
  return (
    <div className="prompt">
      <label className="sr-only" htmlFor="q">
        Input to verify
      </label>
      <form className="prompt-box" onSubmit={onSubmit}>
        <span className="p" aria-hidden="true">
          ❯
        </span>
        {/* native-caret only for wide chars (emoji/CJK), where a per-cell block
            can't track the caret — then the native green caret shows and .cursor
            hides (CSS). For normal ASCII the block cursor shows, native hidden. */}
        <div
          className={`field${WIDE_CHARS.test(input) ? ' native-caret' : ''}`}
        >
          <input
            id="q"
            ref={inputRef}
            type="text"
            value={input}
            onChange={onChange}
            onKeyDown={onKeyDown}
            onKeyUp={place}
            onClick={place}
            onScroll={place}
            onSelect={place}
            maxLength={2000}
            disabled={verifying}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            enterKeyHint="go"
            placeholder="paste an input to verify"
          />
          <span className="cursor" ref={cursorRef} aria-hidden="true" />
        </div>
        <button
          type="submit"
          className={`go${input.trim() !== '' && !verifying ? ' is-ready' : ''}`}
          disabled={verifying || input.trim() === ''}
        >
          {verifying ? 'verifying…' : '⏎ verify'}
        </button>
      </form>
      {/* Prompt hint. Both items are real behavior: ⏎ submits
          the form (onSubmit); ↑/↓ walk submitted-input history (in-memory, this
          session). esc is still not built, so it stays omitted — the hint states
          only true behavior. */}
      <p className="hint">
        <kbd>⏎</kbd> verify · <kbd>↑</kbd> history · /help
      </p>
    </div>
  )
}
