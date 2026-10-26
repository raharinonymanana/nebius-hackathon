# Testing

Mélodie's credibility rests on one claim: **the verdict is decided by a sealed,
model-free replay, and the harness cannot be fooled into proving something that
isn't there.** The suites here exist to keep that claim honest — each one checks
a property a user (or a judge) would otherwise have to take on trust.

Guiding rule: **document the defence, never hand over the attack.** These tests
confirm that guards *fire* (size caps, target whitelist, SQLite hardening,
canary-only verdict); they publish no bypass, and none exists in-tree — every
security test asserts the guard holds.

## The three subsystems

| Subsystem | What it is | Failure looks like | Tested by |
|---|---|---|---|
| Verifier core | deterministic model-free replay + canary verdict | a fixed input stops giving the right verdict; a patched target reads PROVEN | discrimination + harness-integrity suites |
| Security boundary | input cap, whitelist, canary isolation, SQLite hardening, input-as-data | crafted input escapes the sandbox, skips a cap, or defeats the canary | verify-boundary + hardening suites |
| Product surface | Lambda API + React TUI | API 500s, wrong content-type, UI breaks or mislabels a verdict | router + frontend suites + live E2E |

## Offline suites — run in CI on every push

No ConTree, no network, no model calls. `.github/workflows/ci.yml` runs all of these.

| Suite | Covers |
|---|---|
| `tests/advisory_verify.py` | Tavily advisory citation, discard logic, consistency, error handling, malformed-CVE reject |
| `tests/locate_verify.py` | located-unaided measurement, handed-prompt purity, scaffolding-leak guard |
| `tests/advisory_tool_verify.py` | search_advisory dispatch, compacting, per-run call cap |
| `tests/app_router_verify.py` | Lambda router: traversal→404, bad method→405, bad JSON / oversize / missing input→400, no source leak |
| `tests/sqlite_harden_verify.py` | in-sandbox SQLite hardening: ATTACH/DETACH denied, ordinary SQL unaffected |
| `tests/fuzz_input_verify.py` | /api/verify input-validation fuzz: hundreds of hostile bodies are rejected cleanly, handler never 500s |
| `frontend/src/normalise.test.ts` | the runtime honesty boundary: contract-shape guard + verdict-discriminant guard (rejects unknown / spoofed verdicts) |

The workflow has two jobs. `python` lints with ruff, then runs the offline
suites; `frontend` lints with oxlint, runs Vitest, then type-checks and builds.

```bash
# python job: lint, then the offline suites
ruff check .
python -m tests.advisory_verify
python -m tests.locate_verify
python -m tests.advisory_tool_verify
python -m tests.app_router_verify
python -m tests.sqlite_harden_verify
python -m tests.fuzz_input_verify

# frontend job: lint, unit tests, type-check + build
cd frontend && npm run lint && npm run test && npm run build
```

## Live suites — documented, not in CI (need ConTree + a real key)

These spend ConTree sandbox compute but make **no model calls** (zero
Nemotron/Tavily credits). They are excluded from CI because GitHub's runner has
no ConTree access; run them locally with the venv active and `.env` present.

| Suite | Covers |
|---|---|
| `tests/agent_v4_verify.py` | harness integrity: vulnerable+exploit→PROVEN, benign→NOT PROVEN, cheat-exploration / secret-path / cheat-as-payload→NOT PROVEN. Parametrized over any cartridge via `VERIFY_SPEC_PATH`. |
| `tests/ormar_discriminate.py` | ormar matched negative control: bakes 0.22.0 + 0.23.0, runs the five integrity cases, and writes a real `fixed` receipt (patched→NOT PROVEN) that backfills the discrimination row. |
| `tests/verify_service_security.py` | the deployed `verify()` boundary: exploit→PROVEN; benign / oversized / non-whitelist / shell-metachar→rejected or NOT PROVEN; input is data, never shell. |

```bash
VERIFY_SPEC_PATH=targets/starlette/spec.py python -m tests.agent_v4_verify
python -m tests.ormar_discriminate
python -m tests.verify_service_security
```

## Compile-time — enforced by the type-checker

`frontend/src/contract.ts` models a run as a discriminated union on `verdict`:
`human_trace` exists **only** on `ProvenRun`. A NOT PROVEN run therefore cannot
carry a trace — the "watch it happen" beat is structurally proven-only, enforced
by `tsc -b` on every build. This is the G1 honesty property, checked by the
compiler rather than by convention.

## Negative controls (why the suites are trustworthy)

A harness that returns PROVEN for everything is worthless. The suites pin the
negatives, matched against the positives:

- exploit on the **vulnerable** build → PROVEN
- same exploit on the **patched** build → NOT PROVEN  (the matched control)
- benign input → NOT PROVEN
- reading the planted secret during exploration (not via the measured replay) → NOT PROVEN
- a payload echoed back → never executed → NOT PROVEN

`harness discrimination (fixed→NOT PROVEN)` in `/eval` is **1/1 across all four
targets**. ormar's is produced by an explicit model-free matched replay (receipt
`model = "none (model-free replay)"`), disclosed in the eval notes — a
harness-only control, distinct from the other targets' model-driven fixed runs.

## Live end-to-end acceptance (deployed URL, 2026-10-25)

| Check | Result |
|---|---|
| Site loads, terminal UI renders | pass |
| `/api/data` drives UI; `/eval` table renders | pass |
| Real exploit → PROVEN, fresh per-run canary, 6-step trace | pass |
| Benign → NOT PROVEN, different canary | pass |
| Malformed (`DROP TABLE …`) → NOT PROVEN, exit=1, no crash | pass |
| NOT PROVEN framed as the harness working | pass |
| ormar discrimination 1/1 live in `/eval` | pass |

## What this repo deliberately does not contain

- No sandbox-escape or canary-defeat recipe. Every security test asserts a guard
  holds; none demonstrates a working bypass (there is none in-tree).
- No secrets. `.env` is gitignored from the first commit; CI uses a dummy key.
- No untracked eval data. The 31 receipts in `receipts/` are committed as the eval
  dataset, so `python -m prover.eval_report` reproduces from a fresh clone; the demo's
  frozen contract `demo/demo_data.json` is regenerated from them by `demo/build_data.py`.
