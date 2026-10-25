export function EchoRow({ id, text }: { id: number; text: string }) {
  return (
    <div className="echo">
      <p className="cmd">
        <span className="p" aria-hidden="true">
          ❯
        </span>
        {text}
      </p>
      <span className="stamp">#{id}</span>
    </div>
  )
}
