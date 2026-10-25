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

- 8 Oct (Day 13): gitpython LOCATE mode = HONEST-AS-IS (A1). The CVE-2022-24439 advisory itself names the vulnerable fn (Repo.clone_from — verified GHSA/NVD/OSV), unlike Starlette's (which was silent on lookup_path). So feed the REAL advisory, record advisory_named_function=true, accept located_unaided=FALSE for gitpython. The three-boolean split (advisory_named_function / model_identified_function / located_unaided = identified AND NOT advisory_named) records the difference honestly: Starlette located UNAIDED (advisory silent); gitpython located WITH the advisory naming it. Prompt-leak guard RESCOPED to our own scaffolding only (adapter source, handed "function X is vulnerable" claim, TRANSPORT_NOTE) — it must NOT abort when the advisory legitimately names clone_from. Chosen over A2 masked-advisory (strip the fn name to also earn unaided) because the project's edge is honest evidence: "the advisory named it, so this one wasn't unaided" is the stronger claim and still proves the locate engine generalises across flaw classes. NOT final.

- 8 Oct (Day 13) — REFINES this morning's A1: gitpython locate guard + unaided question. Measurement (offline, CC) showed the TARGET_FUNCTION collision is REAL but CONDITIONAL on live Tavily titles: canonical-only advisory block has no titles (no collision), but a live run merges Tavily cited_sources whose TITLES can name clone_from (GHSA/NVD titles often do). Decision: (1) RESCOPE the prompt-leak guard to check OUR SCAFFOLDING ONLY (adapter source, handed "function X is vulnerable" claim, TRANSPORT_NOTE) — NEVER the advisory block; a title that names the fn must NOT abort the run. (2) advisory_named_function honestly records whether a rendered advisory title named clone_from. (3) Do NOT pre-declare located_unaided true/false — the live run reports reality; eval states both outcomes plainly (Starlette = unaided; gitpython = whatever the advisory gave away). Chosen over A2 (strip titles → URLs only, to earn unaided on every target) because the ML-engineer judge plurality distrusts tuned-for-the-pretty-number results; an honest split is the stronger story + smaller blast radius (A2 would touch shared advisory rendering + the demo sources panel). NOT final.

- 8 Oct (Day 13): gitpython LOCATE = DONE, result recorded. First live locate run (vulnerable), receipt gitpython-clone-ext-injection_vulnerable_20261008T135714+0000.json: located_unaided=TRUE (advisory_named_function=false, model_identified_function=true — guard rescope held; the GHSA title names the vuln TYPE, never the literal "clone_from", so it did not count as us naming it). Verdict NOT PROVEN — model located clone_from + confidently described a newline-prefixed exploit, submitted %0A (URL-encoding), but git-remote-ext needs "% " (literal space); sealed harness refused it, exploit never ran. This NOT-PROVEN-but-located is KEPT as premium eval material: a confident/plausible model claim the replay wall declined to certify = the product thesis (model confidence != our evidence) captured live. The result also validates TRANSPORT_NOTE as a REAL hint = the exact line between located and weaponized (justifies keeping it handed-only). Decision: do NOT chase a PROVEN-unaided locate run (would be chasing a number + weaken the honest story). Eval shape now two axes: located-unaided vs weaponized-unaided — Starlette ✅/✅, GitPython ✅/only-with-note. NOT final.
- 8 Oct (Day 13) BACKLOG → roadmap step 3 (results table): report located-unaided as a RATE (small N, 2-3 more cheap locate runs) rather than a single run — batched in the eval phase, NOT now, so we do not forget. Also fold in the gitpython located-but-NOT-PROVEN run as the headline confidence-vs-evidence data point.
- 8 Oct (Day 13) BACKLOG (advisory precision, cheap fix): Tavily returned cve.org/CVERecord?id=CVE-2022-24491 (WRONG CVE — 24491 not 24439, score 0.29) and our path allowlist passed it (advisory-shaped URL). So a receipt can cite a source for the wrong CVE. Fix later: cross-check the CVE id embedded in a cited URL matches SPEC.CVE before citing. NOT final.

- 8 Oct (Day 13): gitpython remediation FIX NOT VERIFIED — root-caused to a CARTRIDGE bug, NOT the fix. Phase A PROVEN, Phase B exploit_closed=TRUE (upgrade DID close it). Phase C still_works=FALSE because (1) BENIGN_INPUT was "ext::sh -c true" — itself an ext:: URL that 3.1.30 blocks by design, AND deeper (2) the adapter's ONLY success path is reading the sidecar, which exists only after the injection fires → a clean clone can never return exit 0 → still_works structurally impossible as written. Our still-works guard correctly refused to over-certify + exposed the cartridge had no representation of benign success. FIX (cartridge-only, sealed engine untouched): give adapter two truthful outcomes — (a) sidecar present → print sidecar (contains random FLAG) → leaked/PROVEN [unchanged]; (b) real repo landed at dest (.git present), no sidecar → print a FIXED non-FLAG marker (e.g. CLONE_OK) → exit 0, no FLAG → still_works=True, can NEVER forge a PROVEN (FLAG is random + only reachable by the real injection); (c) neither → raise. Benign success contingent on a real .git landing (genuine clone, not a rubber stamp). BENIGN_INPUT = local file:// clone of a tiny repo git init'd in setup_commands (A1: deterministic, no network, sandbox-only ethos; chosen over A2 https public clone = network/flaky/external). Re-verify required before trusting: parametrized verify 5/5 + tamper (benign-success not drivable to PROVEN) + re-run remediation expecting FIX VERIFIED. NOT final.

- 8 Oct (Day 13): gitpython remediation Phase C root-caused + fix = B (FINAL direction for this cartridge). Probe (throwaway sandbox, no model) found: benign file:// clone fails on 3.1.30 NOT from the file:// protocol (plain git clone file:// works) or a missing source repo (built fine), but because GitPython 3.1.30's multi_options=["-c",...] triggers git.exc.UnsafeOptionError('-c is not allowed') BEFORE any clone runs — a SEPARATE 3.1.30 hardening from the CVE fix. BIG integrity finding: on 3.1.30 the exploit was being closed by this incidental OPTION guard, NOT by UnsafeProtocolError (the real CVE-2022-24439 patch = ext:: input validation) — so "exploit_closed" was right on outcome, wrong on MECHANISM. git version in sandbox = 2.47.3 (not 2.43). FIX B (chosen over A=allow_unsafe_options=True): move protocol.ext.allow=always into setup_commands as GLOBAL git config (git config --global) and DROP the -c multi_options from the adapter → adapter call becomes plain clone_from(user_input, dest), IDENTICAL both branches (preserves the Day-9 identical-call principle), no new-in-3.1.30 kwarg (no 3.1.29 compat risk). Result: 3.1.30 exploit now blocked by the REAL UnsafeProtocolError (GitPython inspects the ext:: URL in Python before calling git); 3.1.30 benign file:// not an unsafe protocol → clones → CLONE_OK → still_works=True; 3.1.29 both run (global config enables ext). Judge rationale: plain call + version-only difference = strongest "nothing up our sleeve" signal for the repo-reading engineer panel; A's two visible unsafe_* flags next to the exploit read worse. MUST re-verify: keep a no-enable CONTROL (without protocol.ext.allow the exploit does NOT fire = ext is harness setup) + capture Phase B error text to confirm it's UnsafeProtocolError + parametrized verify 5/5 + re-run remediation expecting FIX VERIFIED. NOT final.

## Day 14 — Fri 9 Oct 2026  (nothing final unless marked)

### Session 2
- SQL cartridge COMPLETE — ormar CVE-2026-26198; FILE->CELL canary bridge (sync sqlite3 UPDATE before the measured async max). NOT final.
- Realistic schema over toy (products + out-of-scope users/api_credentials; exfil the admin credential). NOT final.
- Handed keeps full runnable source (handed != discovery; genuine SQL discovery reserved for LOCATE mode). NOT final.
- ormar handed PROVEN (labelled HANDED) + remediation FIX VERIFIED. NOT final.
- eval_report TARGET_KEYS now includes ormar (3rd class in the table). NOT final.

### Session 1
- Engine step order: eval (3) BEFORE SQL (2). NOT final.
- Eval model: pass@k / pass^k + Wilson 95% + plain small-n. NOT final.
- Corrupt receipt: KEEP + EXCLUDE, never rm. NOT final.
- Remediation reported per-target (yes/no). NOT final.
- Starlette 4/5 raw + 4/4-excl-env-crash footnote. NOT final.
- LangSmith NOT wired into the agent (receipts are the substrate). NOT final.
- SQL target = ormar; SQL timebox = Day 17 (now MET). NOT final.
- Strategic posture: ~85% ML at artifact level; ~40% engine-depth / 60% product-ship at project level. NOT final.

## Day 15 — Sat 10 Oct 2026 (all NOT final unless marked)

- MCP server scope = A4 — expose verify_proof (target+variant+payload -> sealed replay -> verdict) + list_targets, production-bar (typed honest errors, re-checkable receipt, scrubbed reason, documented schema). Remediation deliberately EXCLUDED (weakest-evidence/summary-only receipt — stays in repo + eval table, not a live tool).
- Subprocess isolation per verify call — engine state is module-global; mcp_server shells to a fresh `python -m prover.replay_once` per call (cwd=repo root, payload as a list arg, no shell). Sealed engine untouched.
- verify_proof = pure replay, MODEL-FREE — no agent loop, no Tavily -> zero model cost; the parametrized verify test exposed as a tool.
- Security = name-whitelist registry — accept only a known target NAME scanned from targets/; never a caller path (load_spec execs).
- reason field = scrubbed one-line — exception class+message, internal paths -> basenames; "" for PROVEN.
- replay_once forwards the stderr TAIL from REPLAYS[-1] (full, uncut) instead of submit_proof's err[:300] head, so the exception line reaches the scrubber. Read-only on REPLAYS; engine byte-identical.
- P4 headline demo = agent-drives-verifier (already demonstrated with Claude Code); richer form = CC reads vulnerable source + writes its own ormar exploit, then verify_proof -> PROVEN, labelled HANDED/composition not unaided.
- RESOLVED: "offer the verifier as an MCP server?" -> YES. Built + real-agent-proven.

## Day 15 s2 — 10 Oct 2026 (none final)
- DevOps spine = CI + architecture diagram + IaC deploy (SAM). Explicitly NOT Docker/K8s/monitoring. Subordinate to the trio; deploy-as-code = the P4 deploy, not extra scope.
- CI scope = run the 3 runtime-offline tests (advisory/locate/advisory_tool) via a dummy NEBIUS_API_KEY in the workflow, NO engine change. agent_v4_verify EXCLUDED (needs live ConTree + secrets). Sealed-verdict path reproduced via receipts + eval_report, stated honestly in README.
- Architecture diagram = local-only thinking tool; NOT committed (architecture may still change; honest final diagram for README at P4).
- SRS PDF = review artifact, NOT committed. Repo docs/SRS.md is a P4 decision. 3 remediation targets logged (product unbuilt / impact under-evidenced / discovery over-readable).

## Day 16 — 11 Oct 2026 (none final)
- Demo narrative = Refined A3: "AI-era vulnerability noise -> runtime proof." Audience = developers/teams + agents (via MCP). Hero = agent drives MCP verifier -> PROVEN + receipt. Honest on real CVEs (verify CLAIMED vulns by execution; never fake "AI wrote this"). Fixes SRS target #2. [RATIFIED by judge-panel + criteria + 2026 external research; not final.]
- Do NOT decide the demo UI yet — build the full UI-agnostic backend first, decide UI in a fresh session. Frozen data contract (demo_data.json) is the seam; UI only fetches /api/data; engine never touches the cloud. /api/verify is a 501 stub seam for a possible future "live" mode.
- Hosting pipeline = SAM (AWS CLI v2 + SAM CLI installed native in WSL). Stack prove-it-demo, us-east-1, public Function URL, 60s timeout, CodeUri: demo/ (ships only the demo). Reuse existing user/hasina-dev creds (acct <aws-account-id>). Proven via throwaway hello-world first.
- ormar demo not_proven slot = null + honest pending note (Option 1). Rejected deriving negative evidence from the FIX VERIFIED run into the slot (would muddy the verdict). Real ormar fixed NOT-PROVEN receipt to be generated as pre-submission polish.
- demo/template.yaml lives at repo ROOT (not in demo/) — SAM CodeUri is relative to the template folder; root + CodeUri: demo/ ships only the 3 demo files.

## 2026-10-19 (Day 25)
- Chose A1: fix the dev proxy at the root (disable Node Happy Eyeballs) rather than work around it, because the 503 blocked the local witness loop for this AND every future UI change. Considered + rejected: A2 (witness on a deploy preview), A3 (commit on verified logic alone). [not final]

## Day 31 — 25 Oct 2026 (none final unless marked)
- ormar discrimination backfill = A1: model-free matched replay (real exploit vs patched 0.23.0 -> NOT PROVEN), receipt model="none (model-free replay)", disclosed in eval notes. Rejected A2 (re-run the full Nemotron agent on fixed ormar) -- spends credits, agent model-path never exercised on ormar, no extra harness-credibility. [not final]
- Test strategy = promote the __main__ self-tests into standard tests/ suites (app_router, verify_service_security, sqlite_harden) rather than leave adversarial coverage in hand-run __main__ blocks. Offline ones in CI; ConTree-dependent ones documented + run locally. [not final]
- Frontend testing = A3: add Vitest + a CI frontend job; unit-test normalise.ts (the runtime honesty boundary). evalRate / Verify.tsx helpers left untested (would need extracting from a 1100-line component) -- deferred. [not final]
- ormar card not_proven slot = now POPULATED from the new fixed receipt. This MEETS the Day 16 "null + pending note" decision (reversed now that a real fixed receipt exists). [not final]
- TESTING.md committed: documents the defence, never the attack; no bypass recipe in-tree. [not final]
