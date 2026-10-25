import { HELP } from '../lib/commands'

export function HelpBox({ id }: { id: number }) {
  return (
    <section
      className="box about"
      aria-labelledby={`help-h-${id}`}
    >
      <h2 className="box-title" id={`help-h-${id}`}>
        help
      </h2>
      {/* HELP rendered verbatim — dim, whitespace preserved, same
          monospace block treatment as the banner above. */}
      <pre
        className="dim"
        style={{
          margin: 0,
          font: 'inherit',
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
        }}
      >
        {HELP}
      </pre>
    </section>
  )
}

export function OutputBox({ id, title, body }: { id: number; title: string; body: string }) {
  return (
    <section
      className="box about"
      aria-labelledby={`out-h-${id}`}
    >
      <h2 className="box-title" id={`out-h-${id}`}>
        {title}
      </h2>
      <pre className="cmd-out dim" style={{ margin: 0, font: 'inherit' }}>
        {body}
      </pre>
    </section>
  )
}
