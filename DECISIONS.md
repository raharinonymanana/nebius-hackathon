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

## 2026-09-30 (not final)
- Fallback plan: if Sandboxes beta access has not arrived by Thu 1 Oct Day 3 slot, swap in Day 5 (OpenShell + NemoClaw + Hermes on WSL) first; Day 3 resumes when access arrives.

## Thu 1 Oct 2026 (not final)
- Keep native Docker Engine inside WSL; do not install Docker Desktop for now. NemoClaw docs only name Docker Desktop (WSL backend) as tested on WSL2, so ours is untested. Revisit if onboarding fails on Docker.
- WSL memory limit 10 GB (leaves about 5 GB for Windows). Revisit if Windows struggles.
- Open question 1: NemoClaw's default agent is OpenClaw. Check whether Hermes runs under NemoClaw or needs OpenShell directly.
- Open question 2: NemoClaw default inference is the NVIDIA Endpoint (build.nvidia.com), not Nebius. Check that a custom OpenAI-compatible provider can point at Token Factory. This is the make-or-break test for Area A.

## Thu 1 Oct 2026, later (not final)
- Pin NemoClaw to commit 6f3cced4230ae9660c049cc11804daf37797c595 (= lkg = v0.0.124) via NEMOCLAW_INSTALL_REF, for a reproducible install. Revisit if v0.0.124 has WSL bugs fixed in v0.0.125-129.
- Run the installer from the downloaded file with --defer-onboarding, then onboard separately with the custom OpenAI-compatible provider pointing at Token Factory.

## Thu 1 Oct 2026, 09:50 (not final)
- Redo install from scratch with the same pinned commit and the downloaded /tmp/nemoclaw.sh, answering n at the Express prompt. Never use --delete-models on uninstall (deletes all Ollama models and ~/.cache/huggingface).
- Do not repeat a defer-onboarding install followed by nemohermes uninstall before a gateway exists unless we want to hit the same error again; if cleanup is needed again, use the manual path list in LOG.md.

## Thu 1 Oct 2026, 10:47 (not final)
- A1: single engine = Docker Desktop, per-user install, WSL 2 backend; WSL integration only for Ubuntu-24.04 (leave vps-practice off); Resource Saver off. User accepts Docker's license terms themselves in the app (free for personal use and education per Docker's docs).
- Time-box: if Docker Desktop shows an endless starting spinner or docker info returns HTTP 500 for more than about 5 minutes, stop and log it (fallback A3: park the NemoClaw test, record the Area A feasibility finding). Do not debug kernels or update WSL.

## Thu 1 Oct 2026, 11:03 (not final)
- Docker Desktop is now the single container engine for this Ubuntu; native Docker units stay disabled. Revisit only if Docker Desktop causes RAM trouble during onboarding.
- Next: onboard with custom OpenAI-compatible provider (Token Factory), model nvidia/nemotron-3-super-120b-a12b, --no-gpu, policy tier restricted, web search off, sandbox name hermes-lab.

## Thu 1 Oct 2026, 11:15 (not final)
- Area A feasibility so far: NemoClaw + OpenShell + Hermes runs on Windows/WSL (Docker Desktop) with Token Factory and Nemotron Super as the model. Still to test: tool use inside the sandbox, the blocked-egress approval flow, memory/skills persistence.
- Open question for the security story: the restricted tier still allows broad POST to nousresearch.com; decide whether to tighten that preset.
- Cost design note: every Hermes call carries about 16.7k input tokens of baseline; plan prompts and the cost log around that.

## Thu 1 Oct 2026, 11:30 (not final)
- Candidate demo storyline for Area A (Personal AI): a private agent with a visible cage: allowed vs denied egress, then the blocked request becomes a proposal that only the human can approve. Needs the approval flow tested before it is a decision.
- Open items before any security claim: identify the 3 skipped Landlock paths; decide whether to tighten the nousresearch.com GET/POST /** rule in the baseline.

## Thu 1 Oct 2026, 11:52 (not final)
- Policy: keep the four python3.13 rules rejected; keep the example.com (curl only) approval in the running sandbox as a documented test artifact; no baseline change today. It disappears if the sandbox is recreated.
- Open: whether to allow Hermes's POST /api/show on inference.local (Hermes wants model info; allowlist denies it).
- README security notes must say: tested one IP/port/TCP escape path, not UDP/ICMP/DNS tunneling; pypi preset lets the agent install packages at runtime.

## Thu 1 Oct 2026, 12:02 (not final)
- Area A feasibility evidence now covers: install on WSL (needs Docker Desktop), Token Factory + Nemotron Super route, sandbox file and network enforcement (our own probes), human approval flow, memory across sessions. Not covered: skills, scheduled/always-on behavior, messaging channels, Tavily web search, hosted demo URL.
- Test artifacts left in the sandbox: /sandbox/hello.txt, the example.com (curl only) approval, two test lines in memories/USER.md. Decide at wrap-up whether to clean them.
