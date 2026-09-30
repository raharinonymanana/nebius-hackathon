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
