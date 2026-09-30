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
