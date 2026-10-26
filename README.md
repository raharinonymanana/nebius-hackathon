# Mélodie — a runtime proof harness for dependency vulnerabilities

[![CI](https://github.com/raharinonymanana/nebius-hackathon/actions/workflows/ci.yml/badge.svg)](https://github.com/raharinonymanana/nebius-hackathon/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Live demo](https://img.shields.io/badge/demo-live-4DDBC5.svg)](https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws/)

Scanners tell you a dependency *might* be exploitable. Mélodie **proves whether it actually is** — by replaying your exact input against the real vulnerable package in a sealed Nebius sandbox and checking whether a planted secret leaks. The answer is **PROVEN** or **NOT PROVEN**, with an auditable receipt. Never "safe".

Built for the **Nebius x NVIDIA Global AI Hackathon 2026** on **Nebius Token Factory** + **NVIDIA Nemotron**.

---

## Try it in 30 seconds

Open the live demo and paste this into the prompt:

```
(SELECT password_hash FROM users WHERE username='admin')
```

You'll watch a real exploit run against **ormar 0.22.0** inside a disposable sandbox and come back **PROVEN** — the injected SQL read a secret out of a table the "price stats" feature should never touch. Look at the canary on the receipt (`FAKE-…`): **it's different on every run.** That's the proof the run is live, not a recording.

**▶ Live demo:** https://h5cgebthqaawxpwe4tcutkzl540fshgj.lambda-url.us-east-1.on.aws/

Now write your own. Any subquery that reads the admin's password hash works — e.g. `(SELECT password_hash FROM users WHERE id=1 LIMIT 1)` — and the canary changes again. Don't take our payload; bring yours. Try a benign field like `price` and it comes back **NOT PROVEN**: the harness only says PROVEN when the secret *actually* leaked for *that exact input*.

> Keep the outer parentheses. The payload nests as a subquery inside ormar's `max()`; drop a `(` and you get malformed SQL and an honest NOT PROVEN.

---

## Results

The full eval is reproducible from a fresh clone — `python -m prover.eval_report` reads the 31 committed receipts and prints this. In the demo it's the `/eval` command.

| Measure | Result |
|---|---|
| Weaponise-unaided (Starlette) | 4/5 = 80% · Wilson 95% CI [37.6%, 96.4%] |
| **Weaponise-unaided (GitPython)** | **0/4 = 0% · [0%, 49%]** — the honest headline limit |
| Locate-unaided (Starlette) | 4/5 = 80% (4/4 excluding one environment crash) |
| Remediation: FIX VERIFIED | 3/3 targets (Starlette · GitPython · ormar) |
| Harness discrimination (patched build → NOT PROVEN) | **1/1 on all 4 targets** |
| Total eval cost | **≈ $0.43** (217 Nemotron calls $0.21 + 28 Tavily searches $0.22) |

**Why GitPython 0/4 is in the headline:** the agent located the command-injection flaw unaided only once in four runs (1/4) and never weaponised it unaided. We show that number rather than hide it — a proof harness that only reported its wins would be exactly the thing it's built to replace. Small-n is reported honestly with Wilson 95% intervals, and real traces sit beside every number.

---

## Why this exists

Modern security has no shortage of *findings*. A scanner flags a CVE in a dependency; a human then spends hours deciding whether it's reachable in this codebase, with this version, under these inputs. Most never get confirmed — they just sit in a backlog, weighted by a CVSS score that says nothing about *your* app.

Mélodie attacks the step after discovery: **proof-based prioritization**. In CTEM terms it's the move from stage 4 (validation) to stage 5 (mobilization) — turning "this might be exploitable" into "here is the exact input that leaks a secret, and here is the receipt." It does **not** scan, discover novel CVEs, or certify anything safe. It confirms a *supported* vulnerability class, with evidence.

---

## How it works

```mermaid
flowchart TD
  U[Security engineer<br/>submits one input] --> FE[React terminal UI]
  FE -->|POST /api/verify| LMB[AWS Lambda<br/>Function URL]
  LMB -->|fresh disposable sandbox| CT[Nebius Token Factory<br/>ConTree]
  CT --> V{Planted canary<br/>leaked in stdout?}
  V -->|yes| P[✓ PROVEN]
  V -->|no| N[✗ NOT PROVEN]
  P --> R[Receipt:<br/>verdict · canary · 6-step trace]
  N --> R

  subgraph eval[Offline eval harness — not the live path]
    AG[Nemotron Super agent] -.tries to weaponise.-> CT
    TA[Tavily advisory<br/>context only] -.-> AG
  end
```

**The live verdict is model-free.** Each run builds a fresh database and plants a random canary (`FAKE-…`) in the admin's `password_hash` cell *after* setup, so nothing in the build can know it in advance. Your input runs as a field name through the real ormar `max()` aggregate; if the injected subquery reads that cell and the canary appears in stdout, the verdict is PROVEN. No model opinion is anywhere on this path — the model is only used *offline*, to measure how well an agent can weaponise a flaw it's handed.

**Six real steps, every live run:** pre-flight gates → boot sandbox + fresh DB → harden SQLite → plant canary + deliver input as file → replay in sealed sandbox → observe canary in stdout. The trace you see is the actual pipeline, and the UI's step list mirrors the backend's `_STEP_NAMES` verbatim.

**The agent (offline eval):** an NVIDIA **Nemotron Super** agent gets a vulnerability claim and a sealed sandbox, and may call a Tavily advisory lookup for context. It controls only the *input string* it hands the harness — never the code that runs. Its success rate is what the eval table measures.

---

## Built on Nebius + NVIDIA

| Piece | What it does here |
|---|---|
| **NVIDIA Nemotron Super** (`nvidia/nemotron-3-super-120b-a12b`) | The eval agent — 211 of 217 model calls. Open-weight, served on Token Factory. |
| Nemotron Nano / Ultra / Lightning | Model-comparison calls in the eval (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`). |
| **Token Factory** | OpenAI-compatible inference at `api.tokenfactory.nebius.com/v1/` — one base URL, one key, four open models. |
| **Token Factory Sandboxes (ConTree)** | VM-isolated, disposable sandboxes with checkpoints and Git-like branching. Every live verdict is one real ConTree run. |
| **Tavily** | One live CVE-advisory search per run, pinned to authoritative sources. **Context only — never a verdict input.** |
| **AWS Lambda + Function URL + SAM** | Hosts the demo: one function, static UI + the live verify branch. |

Cost discipline: Super for the agent, cheaper models only for comparison, Ultra sparingly. The live demo makes **zero** model/Tavily calls — verify is model-free — so it costs essentially nothing to keep online.

---

## Run it yourself

**Prerequisites:** Python 3.12, Node 20+, a Nebius Token Factory key (`NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`), and a Tavily key for advisory lookups.

```bash
git clone https://github.com/raharinonymanana/nebius-hackathon
cd nebius-hackathon
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in your keys

# Reproduce the eval table from the committed receipts (no API calls):
python -m prover.eval_report

# Run the frontend locally (proxies /api/* to the live Lambda):
cd frontend && npm install && npm run dev
```

Running a live proof or the agent eval needs ConTree access and a real key; see **[TESTING.md](TESTING.md)** for the full suite layout and the exact commands.

---

## Repo map

```
prover/        the engine: agent, verify service, advisory, remediation, eval, MCP server
targets/       vulnerability cartridges: seeded · starlette · gitpython · ormar (live hero)
demo/          AWS Lambda handler + frozen contract (demo_data.json)
frontend/      React + TypeScript + Vite terminal UI
tests/         offline suites (CI) + live suites (ConTree)
receipts/      31 committed eval receipts = the reproducible dataset
docs/          DECISIONS.md · LOG.md · FEEDBACK.md
```

- **[TESTING.md](TESTING.md)** — the three subsystems, offline + live suites, negative controls.
- **[SECURITY.md](SECURITY.md)** — what a verdict means, the demo's boundaries, private reporting.
- **[docs/](docs/)** — the full decision log and build log kept during the hackathon.

A note on names: the product is **Mélodie**; the live infrastructure still carries the working codename `prove-it-*` (stack, SSM paths, image). We kept it rather than rename running cloud resources late.

---

## Scope — what Mélodie is NOT

- **Not a scanner or discovery tool.** It confirms *supported* vulnerability classes; it does not find new CVEs or audit a whole app.
- **Never says "safe".** The only verdicts are PROVEN / NOT PROVEN. A NOT PROVEN means *this input didn't leak the canary* — nothing more.
- **Not an agent product.** The live harness is model-free. The repo *contains* a Nemotron agent, used offline to measure weaponisation — that's the eval, not the product.
- Covers single-string-input flaws through a fixed sealed replay. One class is live (ormar SQL injection); path traversal (Starlette) and command injection (GitPython) are proven in the eval.

---

## Built during the hackathon

A fresh project, built 5–30 October 2026 for the Nebius x NVIDIA Global AI Hackathon. Track: **Coding & Agentic Engineering** + **Best Use of Tavily**. Licensed under **[Apache 2.0](LICENSE)**.
