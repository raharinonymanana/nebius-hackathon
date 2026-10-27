# Release and operations

How the live demo is released, watched and kept unchanged until judging ends (Tue 15 Dec 2026, 12:00 PT).

## What is live

| Item | Value |
|---|---|
| Release | `v1.0.0`: an immutable GitHub release, locked to commit `0afebeb` |
| Demo | one AWS Lambda behind a public Function URL: https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws/ |
| Build identity | `GET /api/version` (name, version, commit, build time); the UI footer shows `build v1.0.0 · 0afebeb` |
| Monitor | `.github/workflows/demo-check.yml`: daily, and on demand |
| Cost guard | an AWS Budgets alert on real usage, credits excluded |

The identity is written at build time by `python -m demo.build_info` from `git describe`. The build fails without it, so an unlabelled build cannot be deployed. What is live is what is tagged when these two commits match:

~~~bash
curl -sS https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws/api/version
git rev-parse 'v1.0.0^{commit}'
~~~

## Freeze policy

- **Until we submit (Thu 29 Oct 2026):** docs-only commits are allowed. They are never deployed, so the live demo stays `v1.0.0`.
- **From submission until judging ends:** nothing lands on `main` and nothing is redeployed, with two exceptions, each logged in `docs/LOG.md` and disclosed:
  1. **Redeploy the same tag** if the live build drifts from `v1.0.0`.
  2. **Hotfix `v1.0.x`** if the live demo breaks because of our code: the smallest change that restores the documented behaviour, no new features.
- **Why:** the hackathon rules fix the submission after the deadline and require the demo to keep working, free, until judging ends. A frozen repo keeps what judges read identical to what was submitted; the two exceptions keep the demo working.
- **Not frozen:** the daily check keeps running; security reports (private vulnerability reporting, see `SECURITY.md`) are still read and answered, and any fix follows the hotfix path; alerts are still watched.
- **Side effect:** GitHub disables scheduled workflows in a public repo after 60 days without repository activity. With the last commit by 29 Oct, that lands around 28 Dec, after judging ends.

## The daily check

It runs at 06:17 UTC (11:47 IST) and on demand, from outside, the way a judge uses the demo: read-only token, no checkout, no secrets, curl and jq only. It makes no model calls; each run is three to five sandbox replays in ConTree.

| Check | Expect |
|---|---|
| the demo's example exploit (up to 3 attempts, 15 s apart, to ride out a cold start) | PROVEN, with a canary |
| benign `price` (matched control, no retry) | NOT PROVEN |
| the example exploit again | PROVEN, with a **different** canary (a fresh run, not a reused reply) |
| `GET /api/version` | a real version, not `unknown` |

A failure turns the README badge red and emails the maintainer. GitHub can start a scheduled run late or skip one under load (on 27 Oct it started about 6 hours after its slot). A late or missing run is not a failure: run it by hand.

## If the badge goes red

### 1. Re-run once by hand

~~~bash
gh workflow run demo-check.yml
~~~

Green: transient (cold start, network). Log it and change nothing.

### 2. Still red: read which check failed

~~~bash
gh run view "$(gh run list --workflow demo-check.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --log-failed
~~~

| Failed check | Likely cause | Next step |
|---|---|---|
| version missing, `unknown`, or not the tag | deploy drift: live is not the tagged build | redeploy the tag (below) |
| no response, or an HTTP error | AWS side: throttling, an outage | read the logs with `sam logs --stack-name prove-it-demo --tail`, check AWS Health, re-run later |
| example → NOT PROVEN, or an empty canary | sandbox side: ConTree / Token Factory unreachable, an image or credential problem | reproduce locally with `python -m tests.verify_service_security` (venv + `.env`). Fails locally too: upstream. Passes locally: Lambda configuration (SSM parameter, IAM) |
| benign control → PROVEN | integrity failure: the harness proved something that is not there | defect: hotfix |
| second canary equals the first | freshness failure: a reply is being reused | defect: hotfix |

Never paste `sam deploy` or log output publicly: it can include the AWS account id.

### 3. Upstream outage

The cause is outside our code: change nothing. Record it in `docs/LOG.md`, and in `docs/FEEDBACK.md` if it is a Nebius tool. Re-run until green. During an outage the demo returns NOT PROVEN, never a false PROVEN.

### 4. Our defect

Follow the hotfix path below.

## Redeploy the tag (no code change)

Always deploy from a tag, never from `main`: after a docs commit, `main` describes itself as `v1.0.0-1-g…`, and that is what the footer would show.

~~~bash
git switch --detach v1.0.0
python -m demo.build_info && npm --prefix frontend run build && rm -rf demo/web && mkdir -p demo/web && cp -r frontend/dist/. demo/web/ && sam build && sam deploy
git switch main
~~~

Then confirm `/api/version` shows `v1.0.0` with the tag's commit, and run the check by hand.

## Hotfix `v1.0.x`

1. Make the smallest change that restores the documented behaviour. Commit to `main` (no attribution trailers), push, wait for CI green.
2. `git tag -a v1.0.1 -m "<what broke, what changed>"`
3. Deploy from the tag, as above (identity first).
4. Witness: `/api/version` = `v1.0.1` with the commit from `git rev-parse HEAD`; the footer; the example → PROVEN with a fresh canary; `price` → NOT PROVEN.
5. Run the daily check by hand: green.
6. `git push origin v1.0.1`, then publish an immutable release whose notes say what broke, what changed, and whether the verdict logic changed.
7. Record it in `docs/LOG.md` and `docs/DECISIONS.md`.

## If a budget email arrives

The alert fires at $1 of actual monthly usage (credits excluded) and when the month is forecast past $5. Open Cost Explorer by service. Lambda usage is driven by traffic to the public, unauthenticated URL. The worst case is bounded: with no reserved concurrency, the account's concurrency pool (about 10) caps parallel runs, roughly $100 a month even if saturated around the clock. Expected judge traffic costs close to nothing. Any mitigation is decided at the time and logged.
