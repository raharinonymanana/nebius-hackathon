# CLAUDE.md — operating rules for Claude Code in this repo

Mélodie was built with Claude Code as the "hands": a separate planning chat wrote
per-step briefs, Claude Code edited and tested code from those briefs, and the author
reviewed every change, committed, and deployed. Claude Code reads this file at the start
of every session. It stays in the repo on purpose, as a record of how AI-assisted changes
were constrained.

## What this repo is
A runtime proof harness for known dependency vulnerabilities. A payload is replayed
against the real vulnerable package inside a disposable Nebius Token Factory sandbox
(ConTree), and the verdict comes only from whether a planted canary leaks. See README.md.

## Hard rules
- Verdicts are PROVEN / NOT PROVEN (and FIX VERIFIED for a verified patch) only. Never output
  or imply "safe", "secure" or "prevents". A NOT PROVEN is never upgraded to safe.
- Evidence = the sealed replay harness ONLY. Nothing a model says about its own actions is
  evidence. Never weaken the harness or let a model control harness code.
- Do not spend API credits (Nemotron calls, live agent runs) unless the brief says to.
- Secrets live in .env (gitignored; template in .env.example). Never write a key into a
  tracked file, code, or output.
- Do not install packages or edit requirements*.txt / package.json unless the brief says to.
- Do not edit the records in docs/ (LOG.md, DECISIONS.md, FEEDBACK.md); the author keeps them.
- If a brief conflicts with this file, follow this file and say so.

## Git
- Commit only from an explicit per-file brief: `git add <file>` by name, never `git add .`.
- Commit messages are one line with NO trailers (no Co-Authored-By, no session links).
- Never push and never rewrite history. Pushing and deploying belong to the author.

## Layout
- `prover/`   the engine (agent_v4.py), the model-free live verify (verify_service.py),
              remediation, eval report, MCP server
- `targets/`  one folder per vulnerable target ("cartridge"): spec.py (+ adapter.py).
              The engine never hardcodes a target.
- `demo/`     the Lambda handler (app.py) and the frozen data-contract builder
- `frontend/` the terminal UI (Vite + React + TypeScript)
- `tests/`    offline suites (run in CI) and live suites (need ConTree); see TESTING.md
- `receipts/` the committed eval dataset (one JSON receipt per run)
- `docs/`     decision log, build log, tool feedback

## Commands (activate the venv first: source .venv/bin/activate)
- Offline tests:  python -m tests.<suite>   (full list in TESTING.md)
- Eval table:     python -m prover.eval_report
- Data contract:  python -m demo.build_data
- Frontend:       cd frontend && npm run dev | test | lint | build
- Live agent run (SPENDS credits, only when briefed): python -m prover.agent_v4
