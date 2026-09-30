## 2026-09-30 (not final)
- Keep original 7-day learning plan; run 2 sessions/day x 4h. Decision day moves to Sat 3 Oct, build starts Sun 4 Oct.
- Environment: WSL Ubuntu (NemoClaw is Linux-first, Sandboxes CLI assumes a Unix shell).
- Terminal map: T1 = WSL work terminal, T2 = second WSL tab for long-running processes.

## 2026-09-30 (not final)
- Nemotron 3 Super is the default model for agent tool loops; Lightning excluded from loops until we test it ourselves.
- Design rule: source URLs/provenance are collected by our code from tool results, not trusted from model text.

## 2026-09-30 (not final)
- Provenance receipts are printed by our code after every answer (agent_v3 pattern), reused in the final build.
- Authoritative-domain pinning + source dates to be added to web_search before it is used in the real project.
