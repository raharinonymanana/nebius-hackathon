# archive/

Learning-phase scripts from the pre-build week (26 Sep – 4 Oct 2026).
Real, measured probes that informed the product's design — kept for
provenance, **not** part of the shipped prover.

- `agent_v1/v2/v3.py` — early Nemotron agent-loop iterations (tool calling,
  max_tokens / reasoning-token handling)
- `compare_models.py` — Nano / Super / Ultra / Lightning cost + behaviour comparison
- `sandbox_*.py` — ConTree Sandbox probes (hello, apt install, persistence, branching, debug)
- `mcp_smoke.py` — contree-mcp stdio smoke test (lists 19 tools)
- `trace_test.py` — LangSmith tracing probe

Shipped engine: `prover/agent_v4.py` (its integrity tests live in `tests/`:
`agent_v4_verify.py`, `agent_v4_cheat.py`). Cost evidence: `usage_log.jsonl` at the repo root.
