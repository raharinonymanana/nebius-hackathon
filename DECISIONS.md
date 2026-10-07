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

## Fri 2 Oct 2026 (not final)
- Serverless (AI Cloud): do NOT pay or add a card yet. Check the Builders welcome email and Discord for AI Cloud credits (free check). Decide hosting for the demo URL at build start (Sun 4 Oct).
- Serverless is optional: the hackathon rule is Token Factory OR AI Cloud, and Token Factory + Nemotron already satisfies it. Only the "other Nebius services" README bonus is at stake.
- If we deploy our own app: Docker Desktop is started only for the image build/push step, sandbox stays off.

## Fri 2 Oct 2026, later (not final)
- LangSmith: no card, stay on the free Developer plan (about 5,000 traces/month). Revisit only if the cap is hit.
- LangSmith key: Service Key limited to the one workspace, 90-day expiry. Tracing is opt-in per script, never global in .env.
- Cost log: store facts, derive estimates from a price table verified on 2 Oct 2026 (re-check before 29 Oct, prices have valid-from dates). Old learning-week scripts stay unmigrated.
- Trace evidence for README/video: screenshots only (14-day retention). Check the trace metadata for personal data before publishing any screenshot.
- Hermes baseline is the dominant cost driver (about 97% of Super input billed during Day 5). Input for the Day 7 scorecard and for any Area A cost cap.

## 2026-10-02 (not final)
- Order change: Day 3 and Day 4 first (beta access arrived), Day 7 scorecard on Sat 3 Oct.
- In agent code always pass disposable explicitly (SDK default is True, CLI default is non-disposable).
- Checkpoint chain (non-disposable runs, branch from a saved image) is the mechanism for Area B's "try several attempts, roll back failures".
- CLI: always use a named session (-S NAME) for manual exploration and scripts.

## 2026-10-02 (not final)
- Verdict rule: a vulnerability claim is PROVEN only by replay (fixed harness, model supplies only an input string). Exploration output is never evidence. Verdicts are PROVEN / NOT PROVEN, never "safe".
- MCP evaluated (smoke test only). Not used: our agent is a Nemotron-driven custom loop and the verdict needs our own replay harness. Revisit only if a README mention is useful.
- Before the public repo: create requirements.txt; decide whether usage_log.jsonl stays in the repo.

## 2026-10-03 (Sat, Day 7) — Project choice: FINAL
- FINAL (stated by Hasina): build a finding-validation agent. Input: a claimed security finding + a small code repo. Nemotron (Super by default) explores inside a Token Factory Sandbox; our own replay harness decides PROVEN / NOT PROVEN with receipts; for a PROVEN flaw, the agent proposes a patch and the same payload is replayed on a patched branch (fix accepted only if the attack fails AND the app still works).
- Framing: CTEM stage 4 (Validation); TRS (ThreatGraph) covered stage 3 (Prioritization). Pitch: "Scanners flag; this proves."
- Track: Coding and Agentic Engineering. Bonus target: Best Use of Tavily (advisory/CVE context, authoritative domains, source dates in receipts).
- Built in layers: (1) prover on a small deliberately vulnerable repo, (2) patch + still-works check, (3) optional later: MCP server and/or CI integration.
- Area A (secure personal AI) dropped.
- Wording rule kept: verdicts are PROVEN / NOT PROVEN, never "safe".
- Not decided yet (next): first target repo, exploit-class order (proposed: path traversal, then command injection, then SQL injection, each taught before it is added), hosting (AWS Amplify vs free host vs AI Cloud Serverless).

## 2026-10-03 (Sat, Day 7) — Test targets: ladder (not final)
- Chosen A1: test on real targets, not only our own mock code, as a ladder:
  1. Our small seeded target first (already works), to make the engine solid.
  2. Main proof: real open-source projects in pairs, vulnerable version (expected PROVEN) vs fixed version (expected NOT PROVEN) = a known-answer test set, like the Test Bench.
  3. Stretch: one deliberately vulnerable app (candidates from general knowledge, unverified: OWASP Juice Shop, DVWA, WebGoat) as the showcase.
- Rules: attack only our own copies inside the Sandbox, never live sites; check each target's license before use; say clearly what is ours vs borrowed; pick flaws a single input can trigger.
- Known cost: real software needs dependency install and sometimes a running server inside the Sandbox, which agent_v4 does not do yet.
- Candidates to verify at scope time (Sun 4 Oct).

## 2026-10-05 — Day 8, Task 2 FINAL
- First real target: Starlette StaticFiles path traversal (CVE-2023-29159 / GHSA-v5gw-mw7f-84px). Vulnerable <0.27.0, fixed 0.27.0. License BSD-3-Clause.
- Build order: seeded mini-target first (engine), then Starlette (first real proof).
- Exploit-class order: path traversal -> command injection -> SQL injection, each taught before it's added.

## 2026-10-05 — Day 8, Task 3 FINAL
- Hosting: AWS Lambda + Function URL (NOT API Gateway), on existing AWS credit ($199.71).
- Why: Function URL avoids API Gateway's 29s integration-timeout wall (verified, AWS docs) for our 10-30s Sandbox runs; $0 extra cost; nothing runs/bills when idle so it stays free + online to 15 Dec with nothing to remember to stop.
- Rejected: AI Cloud Serverless (needs $25 card charge + Docker image + bills until stopped); free hosts (cold-start risk during live judging).
- Build-time note: raise Lambda's own function timeout from default 3s to ~60s in Phase 4.

## 2026-10-05
- Repo structure: product vs learning-week exploration separated. 11 standalone probe scripts moved to `archive/` (provenance, not shipped). Product files relocate to `prover/` + `tests/` during Phase 1 Step 2 (piggybacked on the harness rewrite, not a standalone refactor). NOT final — revisit folder naming/packaging before the video.

## 2026-10-05
- Phase 1 target interface = a per-target "cartridge" folder (vulnerable.py / fixed.py / spec.py) that the engine LOADS, replacing the inline VULN_SOURCE string. seeded/ is the first; starlette/ (Phase 2) will be the second, same interface. NOT final — spec fields may grow when the real Starlette target needs pip-install + a different entry path.

## 2026-10-05
- Phase 1 COMPLETE on the seeded cartridge. Verdict wording is PROVEN / NOT PROVEN only; "NOT PROVEN" never upgraded to "safe"/"prevents", even when the model's prose says so. receipts/samples/ holds one committed receipt per branch as demo evidence; live receipts/ gitignored. NOT final — limits (input-triggered flaws only, one exploit class) still to expand in later phases.

- 6 Oct (Day 10): Phase 2 target approach = A1 — pip-install the REAL Starlette (0.26.1 vulnerable / 0.27.0 fixed) into the sandbox checkpoint and replay the real StaticFiles.lookup_path. The branch difference is the installed version, not our source, so the cartridge holds ONE adapter.py, not vulnerable.py/fixed.py. NOT final. Chosen over A2 (vendoring our own copy of lookup_path) because it proves against the real shipped PyPI artifact + the real patch.
- 6 Oct (Day 10): engine gains ONE generic hook — build_checkpoint runs SPEC.setup_commands(VARIANT) (default []) before writing files, so a target can install deps once in the trusted checkpoint, never at replay. Seeded declares none -> unchanged. This IS the Phase 2 capability (engine handles a real external dependency). NOT final.

- 6 Oct (Day 10): make_task() now instructs recon-before-guessing (inspect the filesystem / list dirs / read files, then craft a payload from what was observed), and exploration budget raised to MAX_ATTEMPTS=4 / MAX_SUBMITS=3. NOT final. Prompt+budget only; the harness, verdict logic, and PROVEN/NOT PROVEN wording are unchanged. Fixes a prompt-caused miss, not an engine issue.

- 6 Oct (Day 10): Phase 3 remediation loop = a separate composition layer (prover/remediate.py), engine unchanged; both re-prove and still-works go through the engine's trusted submit_proof replay (one evidence path). Remediation verdict wording = FIX VERIFIED / FIX NOT VERIFIED, scoped to "this proven exploit is closed and benign use still works", never "safe". NOT final.

- 6 Oct (Day 11): A3 Tavily placement = both (NOT final). (1) A mandatory advisory lookup run by OUR code at the start of a run: Tavily include_domains + include_domains_mode="restrict" (door), then our URL-path allowlist for advisory-shaped URLs (gate), then a FIXED_VERSION consistency flag; cited sources + retrieved_at + request_id + credits written into the receipt; filtered snippets passed to the model as CONTEXT ONLY. (2) A model-callable search_advisory tool behind the same two filters, capped per run (Brief 3b). Verdict still comes only from the replay harness; advisory text never sets PROVEN/NOT PROVEN. Rationale: strongest Best-Use-of-Tavily story (protect the $3k bonus) while keeping the trusted harness untouched. Built in two briefs: 3a = module + 2 filters + costlog credit logging + spec CVE constant + tavily-python==0.8.4 pin + offline fixture tests (zero credits); 3b = wire mandatory lookup into the run/receipt + add the model tool + one live run.
- 6 Oct (Day 11): advisory sourcing rule (teaching) = domain pin alone is NOT enough — the probe leaked github.com/NeaamHariri/devsec-benchmark (an unknown third-party LLM-sec benchmark, not an advisory). Our own URL-path allowlist is the second, decisive filter; only advisory-shaped URLs (GHSA advisories / NVD vuln detail / OSV vulnerability / CVE.org record) are ever cited. NOT final.
- 6 Oct (Day 11): Tavily published_date is unavailable in tavily-python 0.8.4 (no include_published_date, no date on results). Receipts record OUR own retrieved_at (UTC) + Tavily request_id instead — dates we measured, not dates we trust from the web. NOT final.

- 7 Oct (Day 12): command injection cartridge CVE PINNED = **GitPython CVE-2022-24439** (A1). Version pair vuln **3.1.29** / fixed **3.1.30** (fixed <3.1.30; 3.1.30 adds input validation that rejects unsafe protocols/options). Vulnerable fn Repo.clone_from(url) — one URL string; RCE CVSS 9.8; in-process, no server; pure-Python pip + needs the git binary. Chosen over A2 ansys-geometry-core (literal shell=True but heavy lib + private-helper sink + unrecognisable). TRADE-OFF ACCEPTED: sink is git protocol/option injection (CWE-78 RCE), NOT literal os.system/shell=True — bends the shell-sink bar, keeps every practical bar + max judge legibility ("one repo URL → arbitrary command"). Build wrinkles: apt-get install git in setup_commands; canary routed via ext::sh -c reading git stderr/GitCommandError. Build-time confirm (3.1.29 reproduces / 3.1.30 blocks / benign clones on both) runs BEFORE the cartridge. NOT final.
