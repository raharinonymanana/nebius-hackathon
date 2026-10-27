// `n` is the run number (runStamps); omitted for echoes that aren't a tallied run.
export function EchoRow({ n, text }: { n?: number; text: string }) {
  return (
    <div className="echo">
      <p className="cmd">
        <span className="p" aria-hidden="true">
          ❯
        </span>
        {text}
      </p>
      {n !== undefined && <span className="stamp">#{n}</span>}
    </div>
  )
}
