# Security

Mélodie is a security tool, so its own boundaries are written down.

## Reporting a vulnerability

Please report privately through GitHub: **Security → Report a vulnerability** on this
repository. Do not open a public issue for a security problem.

## The public demo

- `POST /api/verify` replays ONE fixed vulnerability class (ormar, CVE-2026-26198) in a
  disposable, model-free sandbox. The database is created fresh per request and the
  "secret" that can leak is a random canary token, so there is no real data to reach.
- The endpoint is rate-limited per container and capped globally. **Please do not
  load-test or fuzz the public URL.** The input guards are tested offline instead:
  `tests/fuzz_input_verify.py`, `tests/app_router_verify.py`,
  `tests/sqlite_harden_verify.py` (see TESTING.md).

## What a verdict means

PROVEN means the planted canary leaked inside the sandbox for that exact input.
NOT PROVEN means it did not. It is never a statement that a target is "safe".

## Secrets

No credentials are stored in this repository. The deployed Lambda reads its API key
from AWS SSM Parameter Store at cold start; locally, keys live in a gitignored `.env`
(see `.env.example`).
