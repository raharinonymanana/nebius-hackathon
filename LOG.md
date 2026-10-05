## 2026-09-30
- Created lab folder ~/dev/nebius-hackathon, git init, renamed branch to main.
- Claimed $25 hackathon promo via Devpost form (code arrives by email, not yet applied).
- Next: .env, API key hack-lab, venv, first Nemotron calls.
- Day 1 win: first Nemotron calls via Token Factory OK. Models served: Nano-30B-A3B, Super-120b-a12b, Ultra-550b-a55b, plus Nemotron-3_5-Lightning (new, not yet researched).
- Single-call timings 0.9-1.7s (not a real benchmark). Lightning: 408 output tokens for a 1-sentence answer, probably hidden reasoning tokens (unverified).
- Next: check current prices for the four models, add cost per call to the script.
- Cost-per-call added to compare_models.py (prices from Nebius Nemotron models page; verify vs console Billing > Prices).
- Confirmed: reasoning tokens are billed as output. Lightning: 444/480 output tokens were reasoning. Super 39/79, Ultra 48/84, Nano not reported.
- Per call (same prompt): Nano $0.000022, Super $0.000080, Lightning $0.000117, Ultra $0.000283. Single-call timings vary run to run (noise).
- Rule for agent loops: max_tokens includes hidden reasoning; use generous caps and detect empty/truncated replies.

## Wed 30 Sep 2026 (evening) - Day 2 start
- Built agent_v1.py: first agent loop (1 tool, Nemotron Super via Token Factory, MAX_STEPS=6, empty/truncated-reply guards).
- Result: tool calling works in standard OpenAI format, no deviations. 2 steps, ~$0.0004, reasoning 22/41 tokens.
- Observed: model advice for Log4Shell (2.15.0+) came from memory and is outdated; facts must come from tools.

## Wed 30 Sep 2026 (night) - Day 2: Tavily + agent_v2
- Tavily key stored in .env (gitignored), tavily-python installed, smoke test OK.
- Built agent_v2.py: 2 tools (local CVE lookup + Tavily web_search), system message for routing, tool errors returned to model as data.
- Run: 4 steps, 2 Tavily calls, ~$0.0018. Routing correct, one tool call per step (no parallel calls). Input grew 508 -> 1935 tokens.
- Weakness: model ignored "cite URLs", emitted odd citation markers and over-stated a snippet. Fix next: code collects source URLs itself.
- Builders Program: registered long ago, email verification/credit claim still to confirm.

## Wed 30 Sep 2026 (night) - Day 2: agent_v3 + provenance
- Built agent_v3.py: code-collected provenance (PROVENANCE receipts printed after the answer), system prompt caps web searches at 2 and forbids model-written citations.
- Run: 3 steps, 1 Tavily call, ~$0.0016. Real URLs printed by our code. Step 3 used 657 reasoning tokens (reconciling sources).
- Finding: answer quality dropped (said 2.16.0; v2 said 2.17.1+). Cause: single search returned Dec 2021 blog posts, model called them "latest". Receipts prove retrieval, not currency or authority.
- Next fix: pin web_search to authoritative domains (include_domains) and show source dates in receipts.
- Finished the simulated Contree Playground tutorial. Key takeaway: `contree session` lists every run as a checkpoint; `contree session rollback <uuid>` restores one. Exact real-CLI fork/rollback syntax to be confirmed once access arrives.
- Decided fallback (A1): Day 5 first if beta access is late.

## Thu 1 Oct 2026 (morning) - Builders Program admin
- Builders Program accepted (welcome email 25 Sep). Promo code emails arrived (25 and 30 Sep); to apply in Nebius Billing > Payments.
- Checked inbox: no Sandboxes beta email yet -> fallback A1 active (Day 5 first).
- LangSmith $100 credit: redemption form submitted with Org ID. LangSmith requires a credit card on file to view/use the credits (they say no charge until the free allotment is exceeded). Card not added yet; decide before Day 6, set a usage limit first.
- Still to claim: Tavily $25 (link in welcome email), Toloka/Tandem (optional).
- Tavily $25 credit confirmed on dashboard (Thu 1 Oct): Add-on 0 / 3,125 credits, separate from the free 1,000 monthly. Monthly usage 4/1000 matches our 4 searches (1 credit each). Search budget is not a constraint.
- Clarified (1 Oct): console banner "Trial: $1.00 - 24 days" is only the $1 sign-up trial credit (30 days from sign-up, ends ~25 Oct). It does not reflect promo credits and is not an account expiry. Promo credits expire 90 days from issuance per Builder Program terms (should cover the 1-15 Dec judging window). Earlier "trial may end before deadline" risk downgraded.

## Thu 1 Oct 2026 - Day 5 (pulled forward, decision A1)
- Sandboxes beta email not received, so Day 5 (OpenShell + NemoClaw + Hermes, Area A feasibility) runs first.
- Read official docs: OpenShell = sandbox runtime + YAML policy; NemoClaw = installer/blueprint wrapping OpenShell, default agent is OpenClaw; Hermes = MIT agent, WSL2 install supported.
- Prereq check on WSL: Ubuntu 24.04.4, 12 CPU, RAM 7.4 GB (under 8 GB min), Node 24.20 / npm 11.19, Docker Engine 29.8.0 native in WSL (daemon running), RTX 3050 Laptop visible in WSL, real C: free 177 GB.
- Created Windows-side .wslconfig with [wsl2] memory=10GB (laptop has 15.2 GB). WSL restart still pending, so the new limit is not active yet.
- 09:00-09:35 Prereqs settled: WSL RAM now 9.7 GB after restart (.wslconfig memory=10GB), Docker Engine 29.8.0 responds, real C: free 177 GB. Correction: NemoClaw needs Node 22.19+ (earlier note of Node 20+ came from a third-party page); ours is 24.20.
- Docs verified: NemoClaw supports Hermes (nemohermes CLI); custom OpenAI-compatible endpoint (NEMOCLAW_PROVIDER=custom, NEMOCLAW_ENDPOINT_URL, NEMOCLAW_MODEL, COMPATIBLE_API_KEY) can point at Token Factory; Hermes has built-in Tavily web search.
- Express install on WSL would pick local Ollama, which is not wanted; answer n at the Express prompt.
- Downloaded installer to /tmp/nemoclaw.sh (not piped): 383 lines, sha256 738cb07356dc5638ca91351ef78c1e0af7cb689a4bdf579726408306e282e72c. Bootstrap only contacts github.com/NVIDIA/NemoClaw.git; no sudo/eval/base64 in the bootstrap itself. Real installer code lives in the cloned repo and is not yet audited.
- Default ref is the moving lightweight tag lkg = commit 6f3cced4230ae9660c049cc11804daf37797c595 = v0.0.124 (annotated tag). Newest release is v0.0.129.
- 09:40 Ran pinned installer (6f3cced..., v0.0.124) with --defer-onboarding; answered Y at the Express prompt. Install took 143 s, no sudo prompt, onboarding skipped (no NVIDIA credentials), so no sandbox/model/credentials were created.
- 09:44-09:50 Decided to redo it cleanly (answer n next time). nemohermes uninstall stopped at step 2/6: "Could not remove gateway registration 'nemoclaw': openshell gateway remove failed (exit 1)". openshell gateway list showed "No gateways found". Removed manually by exact path: 7 shims in ~/.local/bin (claude left alone), ~/.nemoclaw (rm -rf needed for read-only git packs), ~/.npm-global, ~/.npmrc (39 bytes, only the installer's prefix line), and 6 installer lines from ~/.bashrc (backup ~/.bashrc.bak-before-nemoclaw-removal). The uninstaller itself had already removed the systemd gateway service and ~/.config/openshell.
- Verified clean: no nemo*/openshell commands, none of the paths remain, no systemd units; my claude binary and Docker images (test-bench:step3, test-bench:latest, hello-world) untouched.

## Thu 1 Oct 2026, 10:05-10:47 - Docker blocker on WSL
- nemohermes host probe (v0.0.124) = incompatible. Blocking findings: host.platform.wsl_native_docker_unqualified, host.gpu.container_toolkit_missing, host.gpu.cdi_missing. Per the System Readiness docs, an explicit CPU-only onboarding (--no-gpu) waives the two GPU findings; native Docker Engine inside WSL is not waivable. Qualified WSL runtimes: Docker Desktop (WSL backend) or rootless Podman.
- Decision A1: one engine only, Docker Desktop (per-user install, WSL 2 backend).
- RAM measured: Windows 15.2 GB total, 4.3 GB available; vmmemWSL 1.7 GB, chrome 3.3 GB, claude 1.0 GB, Code 0.9 GB. .wslconfig memory=10GB is a ceiling, not a reservation.
- Backed up Test Bench images: ~/docker-backup/test-bench.tar (72 MB), manifest lists test-bench:step3 and test-bench:latest.
- Versions: WSL 2.7.12.0, kernel 6.18.33.2-2, Windows 11 Home Single Language build 26300 (meets Docker's WSL 2.1.5+ / build 22631+ requirements). Docker issues #391/#397 report Docker Desktop 4.73.0 failing on user-compiled 6.18 kernels (May 2026); behavior on the stock 6.18 kernel is NOT confirmed.
- Stopped and disabled native docker, docker.socket, containerd; removed stale /var/run/docker.sock. Undo: sudo systemctl enable --now docker.socket docker containerd.
- Downloaded Docker Desktop Installer.exe (x86_64, from desktop.docker.com): Authenticode Valid, signer Docker Inc (Palo Alto), 599 MB, SHA256 C139124C9CF71477DC565C3C0EA5A18F90B93D68EBE9AAA848A065960416C0BC. Not installed yet.

## Thu 1 Oct 2026, 10:50-11:03 - Docker Desktop in, blocker cleared
- Installed Docker Desktop v4.93.0 (per-user, WSL 2 backend), skipped Docker account sign-in, accepted terms myself. Engine reached "Engine running" with no startup hang on stock WSL 2.7.12 / kernel 6.18.33 (the May 2026 6.18 issues concerned user-compiled kernels).
- Enabled WSL integration for Ubuntu-24.04 only (vps-practice left off). Ubuntu-side docker now reports Operating System: Docker Desktop, Server 29.8.1; contexts: default (unix:///var/run/docker.sock) + desktop-linux; docker.sock recreated by Desktop.
- Docker Desktop idle RAM shown in its status bar 4.06 GB; Windows available RAM 3,194 MB after setup (4,348 MB before).
- nemohermes host probe after the switch: status inconclusive, only warning host.platform.wsl_gpu_passthrough_inconclusive. wsl_native_docker_unqualified, container_toolkit_missing and cdi_missing no longer reported.
- Restored Test Bench images from ~/docker-backup/test-bench.tar via docker load (test-bench:step3 260MB, test-bench:latest 237MB).
- Side issue: a WSL tab opened from PowerShell is a login shell and did not load ~/.bashrc (no ~/.profile), so nemohermes was "command not found" until source ~/.bashrc.

## Thu 1 Oct 2026, 11:04-11:13 - NemoClaw + Hermes onboarded on WSL, Token Factory route works
- Ran nemohermes onboard --non-interactive --no-gpu --name hermes-lab with NEMOCLAW_PROVIDER=custom, endpoint https://api.tokenfactory.nebius.com/v1, model nvidia/nemotron-3-super-120b-a12b, openai-completions, policy tier restricted, web search none, key read from .env (NEBIUS_NEMOCLAW_KEY) at launch. Preflight saw Docker Desktop, 12 vCPU / 9.7 GiB, added 3072 MB swap, sandbox GPU disabled.
- Result: sandbox hermes-lab Phase Ready (created in about 100 s), Hermes Agent v0.20.6, gateway healthy, route inference.local -> compatible-endpoint -> Nemotron Super, status reports inference healthy.
- Live policy (restricted tier): filesystem read-only system dirs, read-write only /sandbox, /tmp, /sandbox/.hermes, runs as user sandbox, Landlock compatibility best_effort. Network: inference.local (OpenAI-style paths), nousresearch.com and hermes-agent.nousresearch.com (GET/POST any path), integrate.api.nvidia.com (listed paths), pypi.org and files.pythonhosted.org (GET).
- Ports: dashboard 18789 and Hermes API 8642 both answer HTTP 200. Inside WSL they are held by openshell processes bound to 0.0.0.0; on Windows they listen only on 127.0.0.1 via wslrelay (not exposed to the LAN, checked from the Windows side). Onboarding printed a warning that 8642 is held by a listener it cannot attribute, while openshell forward list showed no forwards; the API works, so I read it as a mis-detection (unconfirmed).
- First end-to-end prompt through the Hermes API (one-word reply "pong"): usage prompt_tokens 16715, completion_tokens 24, total 16739. At listed Super prices (0.30 in / 0.90 out per 1M, unverified vs console) about $0.005 per call. Not yet confirmed in the Token Factory console that the hack-nemoclaw key made this call.

## Thu 1 Oct 2026, 11:17-11:29 - Hermes launch and sandbox security probes
- nemohermes launch hermes-lab first failed ("Launch readiness final validation failed due to health") because the 8642 forward process was not recognized by NemoClaw. Both forwards were openshell "forward service hermes-lab" processes (user hasina_rindra, parent /init, bound 0.0.0.0 inside WSL; only 127.0.0.1 on the Windows side via wslrelay). Stopped only the 8642 process after matching its full command line, then nemohermes hermes-lab recover returned result=ready, forwardAction=restored; launch then worked.
- Hermes TUI: nemotron-3-super-120b-a12b, 24 tools, 78 skills. The 4-command test run through the model matched expectations (user sandbox, /sandbox listing, write in /sandbox ok, write in /etc Permission denied).
- Independent probes via nemohermes hermes-lab exec (no model involved): uid=998(sandbox); write /etc denied; write /var/tmp denied although /var/tmp is drwxrwxrwt (so the denial comes from the sandbox file rules, not plain permissions); curl pypi.org = 200 (log: ALLOWED, policy:pypi); curl example.com = CONNECT tunnel failed 403 (log: DENIED, reason: endpoint example.com:443 is not allowed by any policy); curl --noproxy = could not resolve host; raw TCP to 1.1.1.1:443 = connection refused.
- Sandbox log: Landlock ABI V2, compat BestEffort, ro:12 rw:5, rules_applied:14 skipped:3 (the 3 skipped paths are not identified yet). A denial produced "proposals=1" / "persisted draft chunks": a policy proposal awaiting human review (approval flow not yet tested).
- Not tested: UDP, ICMP, other ports/IPs, DNS tunneling. This is not a full escape test; do not claim one in the README.
- Hermes warnings seen: Tirith scanner not available (pattern matching only); SQLite 3.46.1 flagged vulnerable to the WAL-reset bug (journal_mode=DELETE fallback); startup could not open /sandbox/.hermes/state.db.fts_rebuild.lock (Permission denied, cause unknown).

## Thu 1 Oct 2026, 11:36-11:51 - Approval flow tested (OpenShell TUI) and audit log read
- openshell term showed hermes-lab with 5 pending network rules, all L4: example.com:443 (curl, ours from the probe) and four from Hermes's own python3.13: raw.githubusercontent.com, nousresearch.github.io, models.dev, github.com. Detail view of two entries: denied 1 connection each, all at 05:50:42 UTC (3 s after the Hermes session started), review note "rule requires review; no additional risk detected", confidence 65%.
- Pressed a on example.com only (harmless test host): log (UTC) 06:12:36 ApproveDraftChunk, CONFIG:APPROVED add-rule allow_example_com_443 endpoints=[example.com:443] binaries=[/usr/bin/curl] version v2 hash fceaa9cb...; sandbox reloaded the policy at 06:12:41; curl example.com then 200, curl github.com still 403. The approval is bound to host, port and program (curl only) and lasts until the sandbox is destroyed/recreated (docs).
- Rejected the other 5 pending entries (including a second github.com entry from our curl probe) at 06:18:50-06:18:58 UTC: five RejectDraftChunk log lines. Pending badge cleared. Did not press A (approve all).
- Log evidence: Hermes's four denied hosts were a one-time burst at 05:50:42 UTC with no retries in the lines read; hermes-agent.nousresearch.com GET /docs/api/model-catalog.json was allowed (policy nous_research). Just before, a uv process fetched about a dozen packages from PyPI (aiohttp, edge_tts, certifi, ...) under the pypi preset.
- inference.local POST /api/show was denied twice (05:50:42 and 05:54:20 UTC): not in the managed_inference allowlist. The Hermes status bar showed "ctx --"; link between the two is a hypothesis, unverified.
- Not recorded in the log: who approved or rejected; rejection lines do not name the host.

## Thu 1 Oct 2026, 11:54-12:01 - Hermes memory tests
- Asked Hermes to save the fact "codename blue-heron-42" to persistent memory. Hermes reported the path /sandbox/.hermes/profiles/default/memories/user.json and a capacity of 1,375 bytes (50 bytes used). Checked from the host with nemohermes exec: that path does not exist. The fact is in /sandbox/.hermes/memories/USER.md (owner sandbox, mode -rw-------, 50 bytes, plain text, exactly one sentence). Hermes's byte count was right, its path was wrong, its capacity claim is unverified.
- The codename also exists in /sandbox/.hermes/.hermes_history and /sandbox/.hermes/runtime/state.db: raw prompts and conversations are stored in plain text inside the sandbox.
- Fresh session test 1 (ask for the codename): correct answer blue-heron-42, but the trace showed two grep calls, a failed read_file ("File not found: user") and a failed memory call ("Unknown action 'None'. Use: add, replace, remove"); Hermes said the value came from the initial system prompt. Confounded because the fact also sits in history and state.db.
- Clean test: appended a second fact (teal-otter-77) directly to USER.md from the host (file 108 bytes); grep confirmed it exists only in USER.md and in no conversation. Fresh session answered "teal-otter-77" with no tool calls at all. Conclusion (inference by elimination, n=1): the memory file is loaded into the session context at start, and a hand-appended line is accepted.
- Hypothesis, not tested: anything that can write USER.md is injected into all later sessions (memory-poisoning path).

## Fri 2 Oct 2026 — Day 6 (Shipping), session 1
- Sandboxes beta still not granted (Gmail incl. spam checked 06:18 IST; console Sandboxes page still shows "Request beta access"). Day 3/4 stay blocked, Day 6 first.
- Laptop was left stopped by lab-down.cmd. Docker Desktop and the hermes-lab sandbox are NOT needed for Day 6-7 (cloud docs, LangSmith, cost logging, scorecard). They are needed only for Area A / Hermes tests, and for building a container image when we deploy our own app. lab-up.cmd still untested.
- Learned Serverless AI (docs verified): it is a Nebius AI Cloud service, not Token Factory. Endpoint = persistent container with public URL, keeps billing until stopped or deleted. Job = finite container, no public URL, ends by itself. For us: Endpoint = demo URL, Job = optional batch evals. Our Nemotron calls stay on Token Factory, so no GPU endpoint is needed (CPU endpoint is enough).
- Console check (read-only, nothing created, no card entered): console.nebius.com opened straight into a tenant and project default-project-eu-west2. Serverless AI menu is visible (Overview, Devlabs, Jobs, Endpoints). Billing > "Add billing details" form says submitting charges the card $25 to top up the balance. AI Cloud billing is separate from Token Factory; the Token Factory $29.50 is not visibly carried over (unverified).
- Docs say Serverless quickstarts want at least 1 VM in the Compute quota (Administration > Limits > Quotas). Not checked yet, billing first.

## Fri 2 Oct 2026 — Day 6 (Shipping), session 1, continued
- Builders credits checked via Gmail (read-only): the AI Builder Program welcome email lists Token Factory $25, LangSmith $100, Tavily $25, Toloka $50, Tandem $50. NO AI Cloud credit, so Serverless would be paid. Tavily $25 is applied: dashboard Overview shows Add-on 0/3,125 credits (3,125 x $0.008 = $25) next to the free 1,000/month; the Billing page did not show it. LangSmith $100 stays hidden until a card is added (decided: no card).
- LangSmith: free Developer plan (5,000 traces/month, 1 seat, 14-day retention, console button "Add card to remove trace limit"). Created Service Key "hackathon-nebius", scope Specific Workspaces (Workspace 1), 90 days (ends about 31 Dec). Key written to .env via hidden read prompt, never printed. langsmith 0.14.3 installed in .venv.
- trace_test.py: one Nemotron Super call through Token Factory with wrap_openai + @traceable; tracing is switched on inside the script (not in .env) so other scripts stay untraced. LangSmith shows root trace_test_run with one child ChatOpenAI (nvidia/nemotron-3-sup...), 86 tokens, 1.50 s, no cost figure. revision_id in metadata = git commit. Metadata Runtime section not inspected yet. Only screenshots are durable: traces expire after 14 days.
- Console Billing > Prices checked 2 Oct (base rows, eu-north1): Nano 0.06/0.24 (valid 1 Jan 2026), Super 0.30/0.90 (1 Mar), Ultra 1.00/3.00 (1 Jun), Lightning 0.06/0.24 (1 Aug). Each has a -Batch row at half price; no -fast rows for the Nemotron 3 family. costlog.py PRICES_VERIFIED = True.
- Console Billing > Usage 1-2 Oct (full numbers): Super input 253,845 tokens ($0.0761535), output 2,381 ($0.0021429), total $0.0783 before VAT (the $0.09 seen earlier includes VAT). Our usage_log had at most 7,789 Super input tokens, so at least 246k billed tokens did not come from our scripts: consistent with about 14-15 Hermes calls at the 16.7k baseline (arithmetic, not proof). Usage page cannot group by API key (only Project, Region, Label).
- Built costlog.py: log_call() appends facts (ts, label, model, secs, in, out, reasoning, finish) to usage_log.jsonl and never raises; summary() derives cost from PRICES at read time. Verified live via trace_test.py (log line matched the printed numbers). WSL clock is UTC, so ts shows +0000. Old scripts (agent_v1/v2/v3, compare_models) are NOT migrated: learning-week throwaways, the build uses costlog from the first line.

## 2026-10-02 (Fri) - Day 3: Sandboxes (ConTree) DONE
- Beta access email arrived 08:35 UTC (14:05 IST). Console now shows Sandboxes > About, Images, Operations, Files.
- Why: Day 3 proves the core mechanic of Area B (run untrusted code in isolation, checkpoint, branch, roll back).
- SDK (contree-sdk 0.3.6), scripts sandbox_hello/apt/debug/persist/chain.py: code ran in a Nebius microVM (hostname "hostname", kernel Linux 7.0.6), not on our WSL host.
- SDK run() is disposable by default: apt-get update and install in separate calls failed (exit 100, "Unable to locate package"). With disposable=False each run returns a new image and the next run builds on it (sandbox_chain.py).
- Fork: two branches from one checkpoint stayed isolated (A vs B); the parent checkpoint was untouched.
- Timing: apt-get update ~1.0 s; update + install qrencode 4.4 s; small runs ~1-1.5 s.
- Network: apt-get update reached deb.debian.org from inside the sandbox, so outbound internet is open by default. Restricting egress: not tested.
- CLI (contree-cli 0.9.4): profile "default" (type iam) created with `contree auth` from env vars in a subshell; auth.ini mode 600. Session -S day3 verified: use, non-disposable runs (history ids 1-4), branch, checkout, rollback, rollback +1. Rollback is non-destructive (file gone, then back).
- Preloaded public images exist (python 3.10-3.14 variants).
- Not tested: parallel runs, tag command, file upload, MCP server, resource limits/metrics, egress restriction, use from an agent loop (Day 4).

## 2026-10-02 (Fri) - Day 4: prove-it loop with sandbox DONE
- Why: Area B core mechanic. Nemotron Super explores a vulnerability claim in a sandbox; OUR code decides the verdict from evidence it collects itself.
- agent_v4.py: tools run_in_sandbox (exploration, NOT evidence) and submit_proof (one payload string). The fixed harness replays the payload through the real target in a fresh branch of the clean checkpoint, and the model never controls the executed code. Verdict PROVEN only if the replay exits 0 and prints the planted canary (random FAKE-<hex> per run). Limits: 3 explorations, 2 submits, 20 s timeout, 8 steps, 4000 max_tokens. costlog.log_call from the first call.
- First version had a hole: the verdict looked only at output (canary in stdout + exit 0 + text "read_user_file" in the code). agent_v4_cheat.py (code that bypasses the target and prints the secret on a PATCHED target) was wrongly judged PROVEN (prediction confirmed). Fixed with replay verification (decision A1).
- Evidence after the fix: agent_v4_verify.py 5/5 PASS (cheat code with no submit, cheat code smuggled as payload and others stay NOT PROVEN; vulnerable target with ../secret.txt is PROVEN). Live run on the vulnerable target: 3 steps, ~$0.00102, PROVEN by replay, payload ../secret.txt. Live run on the patched target: 4 steps, ~$0.00204, 3 explorations, no submit, NOT PROVEN (correct). Timeout check: infinite loop returns exit 124, timed_out True after ~21 s, no hang.
- Observation: on the patched target the model concluded the claim was "refuted". Our code says only NOT PROVEN. Failing to find an exploit is not proof of safety. Keep this distinction in README and video.
- Known limits: works for flaws triggered by a crafted input string (path traversal, injection), not for flaws that need arbitrary code; a target that echoed its own input could let a payload containing the canary fool the check; a single target and few live runs; exploration stdout is not stored in the printed receipts, so model statements about outputs (e.g. a directory listing) are unverified.
- Cost log total after Day 4 checks: ~$0.0099 across 4 models (Super 24 calls).
- MCP (decision A2, 10 min): pip install contree-mcp 0.5.0 succeeded but the server crashed on import with mcp 2.2.0 (cannot import FastMCP from mcp.server). pip install "mcp<2" (1.30.0) fixed it. mcp_smoke.py started the server over stdio and listed 19 tools; no tool called. HTTP mode not run (docs list no host flag; --http-listen exists in --help). Repo: nebius/contree-mcp, Apache-2.0, Nebius B.V. 2026.
- Not tested: more targets and exploit classes, a stronger model (Ultra) for hard cases, parallel attempts, using the MCP tools.
- TODO before the public repo: requirements.txt (the venv now also holds contree-mcp and the mcp<2 pin).

## 2026-10-03 (Sat, Day 7)
- Scorecard prep done chunk by chunk: decision framing, the 4 criteria, Area A vs B, ideas A1/B1/B2/B3, hosting options.
- Rules check (Devpost rules page): "runs on Token Factory" = runtime call to the Token Factory API, so hosting elsewhere is allowed; criteria are equally weighted; ties broken by Technological Implementation first; demo must stay free and available until judging ends (15 Dec); one Track award + one Bonus award can be combined.
- AWS credits verified in the Billing console (read-only): $199.71 of $200 left, all expiring 08 Sep 2027; the $100 Free Tier credit covers Amplify, Lambda, API Gateway, CloudFront, S3. No credit labelled WeMakeDevs.
- Research 1 (past judging): no past winners for this hackathon (first edition); official updates say judges reward depth within a track (Coding: agent that plans/writes/tests/iterates on a real repo); Nebius Serverless challenge 3rd place = adversarial multi-agent testing tool; winners show measured evidence.
- Research 2 (our strengths): CTEM validation stage matches our pattern (evidence over claims) and continues TRS; ~6% of published CVEs ever exploited (Cyentia/FIRST).
- Decision: finding-validation agent, FINAL (see DECISIONS.md).

## 2026-10-05 — Day 8, Task 1: license + fit check (real targets)
- Verified licenses from each project's own source: Starlette BSD-3-Clause (Kludex/starlette); OWASP Juice Shop MIT (juice-shop/juice-shop); DVWA GPL-3.0 (digininja/DVWA); WebGoat license NOT confirmed -> do not use until confirmed.
- First real target recommended: Starlette StaticFiles path traversal, CVE-2023-29159 / GHSA-v5gw-mw7f-84px. Vulnerable <0.27.0, fixed 0.27.0 (commonprefix -> commonpath). Pure-Python pip pair, single short input string, no server needed (replay via StaticFiles.lookup_path + planted canary).
- Why: fits our replay harness exactly; tiny clean fix (good teaching + patch-step target); matches path-traversal-first order.
- Build-time confirm (not a blocker): verify lookup_path reproduces the traversal without a running uvicorn server.
- Engine-cost ladder: seeded = zero new work; Starlette = needs "pip install in Sandbox" (light); stretch apps = need "run a server in Sandbox" (heavy).
- Rule applied: targets stay as SEPARATE clones, never vendored into our repo, so GPL (DVWA) does not affect our repo license.

## 2026-10-05 — Day 8, Task 2
- Taught path traversal (vs LFI/command injection/SQLi) and the exploration-vs-replay validation model.
- Locked target path + exploit order as FINAL in DECISIONS.md.

## 2026-10-05 — Day 8, Task 3
- Verified API Gateway REST default integration timeout = 29s, configurable but a wall for our runs; Lambda Function URL bypasses it (Lambda timeout up to 15 min applies directly).
- Decided hosting = AWS Lambda + Function URL (A1). Taught Function URL vs API Gateway vs AI Cloud Endpoint.

## 2026-10-05 — Day 8, Task 4 (Phase 0 complete)
- Private GitHub repo live: raharinonymanana/nebius-hackathon. Pushed full history + scaffold (first remote commit fee174e).
- Apache-2.0 LICENSE (full text) + NOTICE + requirements.txt (openai, python-dotenv, tavily-python, contree-sdk, contree-client, langsmith; contree-cli and contree-mcp/mcp<2 deliberately excluded).
- .gitignore protects .env/.env.*/.venv/__pycache__/*.pyc; .env confirmed NOT tracked. usage_log.jsonl kept tracked (cost evidence, no secrets).
- Remote uses SSH origin. gh repo create had half-run earlier (repo existed, origin unset); fixed by wiring origin manually.

## 2026-10-05 (Day 9) — Phase 1 Step 1
- Built seeded mini-target `targets/seeded/target.py`: ~20-line `read_file()` reproducing Starlette's StaticFiles path-traversal bug class (os.path.commonprefix vs commonpath) with a `fixed=True` branch. Build-time confirm PASSES — vuln branch leaks the canary via `../static_secret.txt`, fixed branch blocks it. No deps, no network, no model calls (cost-free by design).
- Why: a fully-controlled zero-cost target to build the replay engine on; makes Phase 2 (real Starlette) nearly free — same bug in real code.
- Repo cleanup: archived 11 learning-week scripts into `archive/` (+README). Product (`agent_v4*`, `costlog`) stays at root; relocation to `prover/`+`tests/` folded into Step 2 to avoid a separate refactor. Why: flat 30-file root buried the engine; separating product from exploration scores on the Design criterion.
