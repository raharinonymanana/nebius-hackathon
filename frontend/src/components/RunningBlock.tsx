import { PIPELINE_STEPS } from '../hooks/terminal-hooks'
import { Verb } from './Verb'

export function RunningBlock({
  verb,
  concept,
  elapsedLabel,
  isFirstRun,
}: {
  verb: string
  concept: string
  elapsedLabel: string
  isFirstRun: boolean
}) {
  return (
    <div className="result" aria-busy="true">
      <p className="verdict">
        <span aria-hidden="true">
          <span className="spin-clover" aria-hidden="true">
            <i className="cd cd1" />
            <i className="cd cd2" />
            <i className="cd cd3" />
            <i className="cd cd4" />
          </span>
          <Verb text={verb} />
        </span>
        <span className="dim stats">
          {elapsedLabel}
          {isFirstRun ? ' · cold start ~12s' : ''}
        </span>
        <span className="sr-only">Verifying — {elapsedLabel} elapsed</span>
      </p>
      <ol className="steps pipeline" aria-hidden="true">
        {PIPELINE_STEPS.map((name, i) => {
          const last = i === PIPELINE_STEPS.length - 1
          return (
            <li key={i}>
              <span aria-hidden="true">{last ? '└─' : '├─'}</span>
              <span className="s">·</span>
              <span>{name}</span>
              <span className="dur" />
            </li>
          )
        })}
      </ol>
      <p className="meta concept" key={concept} aria-hidden="true">
        {concept}
      </p>
    </div>
  )
}
