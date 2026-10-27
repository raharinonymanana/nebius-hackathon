export function TitleStatus({
  runs,
  proven,
  notProven,
  failed,
  verifying,
  inFlightRun,
}: {
  runs: number
  proven: number
  notProven: number
  failed: number
  verifying: boolean
  inFlightRun: number
}) {
  return (
    <>
      <p className="tally" aria-label="Session tally">
        {runs === 0 && failed === 0 ? (
          <span className="dim">no runs yet</span>
        ) : (
          <>
            {runs > 0 && (
              <span className="wide">
                {runs} run{runs === 1 ? '' : 's'}
              </span>
            )}
            {proven > 0 && (
              <span>
                <span className="g" aria-hidden="true">
                  ✓
                </span>{' '}
                {proven}
                <span className="sr-only"> proven</span>
              </span>
            )}
            {notProven > 0 && (
              <span>
                <span className="r" aria-hidden="true">
                  ✗
                </span>{' '}
                {notProven}
                <span className="sr-only"> not proven</span>
              </span>
            )}
            {failed > 0 && (
              <span>
                <span aria-hidden="true">!</span> {failed}
                <span className="sr-only"> run failed</span>
              </span>
            )}
          </>
        )}
      </p>
      <span
        className={`mode${verifying ? ' is-busy' : ''}`}
        role="status"
      >
        {verifying ? <>RUNNING #{inFlightRun}</> : 'READY'}
      </span>
    </>
  )
}
