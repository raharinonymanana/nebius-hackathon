# Nebius x NVIDIA Hackathon — prover (Claude Code operating rules)

This repo is a finding-validation security agent: it PROVES a vulnerability by
replaying a payload against a target in a Token Factory sandbox (patch step later).

## Source of truth
- The canonical plan, decisions, status and schedule live in Hasina's Claude CHAT
  brief, NOT in this repo. This file is only the rules of engagement.
- If a step needs a decision not covered here, STOP and ask Hasina. Do not invent
  scope, pick targets, or change architecture on your own.

## Your role (the "hands")
- You write and run code from an explicit per-step brief. Hasina + the chat = the "brain".
- Do exactly the briefed step. Report the diff/output. Don't expand scope or pre-build
  future steps.

## Hard rules — never break
- Verdicts are PROVEN / NOT PROVEN only. NEVER output or imply "safe", "secure", or
  "prevents". A NOT PROVEN is never upgraded to safe.
- Evidence = the replay harness ONLY. Nothing a model says about its own actions, and no
  exploration stdout, is evidence. Never weaken the harness or let the model control
  harness code.
- Do NOT spend API tokens or run the live sandbox agent (python -m prover.agent_v4,
  Nemotron calls, billable ConTree runs) unless the brief explicitly says to. Local
  confirms only, by default.
- Don't install packages into the venv or edit requirements.txt unless the brief says to.
- Secrets live in .env (gitignored). Never write a key/token into any tracked file,
  code, or output.
- Git is Hasina's. Do NOT commit, push, rewrite history, or change .gitignore.
- Do NOT edit the records: LOG.md, DECISIONS.md, FEEDBACK.md. The chat maintains those.
- Don't touch targets/seeded/, receipts/, or the engine contract unless the brief says to.
- If an instruction here conflicts with a pasted brief, follow THIS file and flag it.

## Build / run commands
- Activate venv first: source .venv/bin/activate  (pip fails otherwise: externally-managed)
- Verdict-integrity suite (no tokens): python -m tests.agent_v4_verify   (expect 5/5)
- Live agent run (SPENDS tokens — only when briefed): python -m prover.agent_v4
- Cost summary: python -m prover.costlog

## Project shape (engine never hardcodes a target)
- prover/ = the product (engine agent_v4.py). tests/ = verdict-integrity suite.
- targets/<name>/spec.py = swappable cartridge the engine loads by file path.
- Clock is UTC in WSL; log timestamps show +0000.
