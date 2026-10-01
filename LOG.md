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
