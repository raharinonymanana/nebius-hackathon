"""Shared cost log.

Stores facts (tokens, seconds) per call in usage_log.jsonl.
Cost is derived at report time from PRICES, so fixing a price later
corrects every old line. Run `python -m prover.costlog` for a summary.
"""
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

LOG_FILE = "usage_log.jsonl"

# Tavily add-on credits. $25 / 3125 credits = $0.008/credit.
# valid-from 2026-10-06; re-check before 29 Oct (same cadence as the model PRICES rows).
TAVILY_CREDIT_USD = 0.008

# USD per 1M tokens: (input, output). Source: console Billing > Prices, 2 Oct 2026.
# VERIFIED 2 Oct 2026 against console Billing > Prices (base rows, eu-north1). Rows have valid-from dates: re-check before 29 Oct.
PRICES_VERIFIED = True
PRICES = {
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06, 0.24),
    "nvidia/Nemotron-3_5-Lightning": (0.06, 0.24),
    "nvidia/nemotron-3-super-120b-a12b": (0.30, 0.90),
    "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
}

# Measured 1 Oct: one Hermes call carried about 16.7k input tokens before our prompt.
HERMES_BASELINE_IN = 16_700


def cost_usd(model, tokens_in, tokens_out):
    """Estimated cost of one call, or None if the model has no price."""
    price = PRICES.get(model)
    if price is None:
        return None
    return (tokens_in * price[0] + tokens_out * price[1]) / 1_000_000


def log_call(model, resp, secs, label=""):
    """Append one record from an OpenAI-style response.
    Never raises: logging must not break an agent run."""
    try:
        usage = resp.usage
        details = getattr(usage, "completion_tokens_details", None)
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "label": label,
            "model": model,
            "secs": round(secs, 2),
            "in": usage.prompt_tokens,
            "out": usage.completion_tokens,  # includes reasoning tokens (billed as output)
            "reasoning": getattr(details, "reasoning_tokens", None) if details else None,
            "finish": resp.choices[0].finish_reason,
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"[costlog] could not log: {exc}", file=sys.stderr)


def log_tavily_call(*, cve, query, credits, request_id=None, response_time=None):
    """Append one Tavily search record to the SAME usage_log.jsonl.
    Never raises: logging must not break a prove/remediation run."""
    try:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": "tavily",
            "kind": "search",
            "cve": cve,
            "query": query,
            "credits": credits,
            "est_usd": (credits or 0) * TAVILY_CREDIT_USD,
            "request_id": request_id,
            "response_time": response_time,
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"[costlog] could not log tavily call: {exc}", file=sys.stderr)


def summary(path=LOG_FILE):
    per = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "unpriced": 0})
    tav = {"searches": 0, "credits": 0, "est_usd": 0.0}
    bad = 0
    try:
        handle = open(path)
    except FileNotFoundError:
        print("No usage log yet.")
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            # Existing model rows have no "provider" key -> treat missing as "model".
            if rec.get("provider", "model") == "tavily":
                credits = rec.get("credits") or 0
                tav["searches"] += 1
                tav["credits"] += credits
                tav["est_usd"] += rec.get("est_usd", credits * TAVILY_CREDIT_USD)
                continue
            try:
                model, tin, tout = rec["model"], int(rec["in"]), int(rec["out"])
            except (KeyError, ValueError, TypeError):
                bad += 1
                continue
            row = per[model]
            row["calls"] += 1
            row["in"] += tin
            row["out"] += tout
            cost = cost_usd(model, tin, tout)
            if cost is None:
                row["unpriced"] += 1
            else:
                row["cost"] += cost

    status = "verified" if PRICES_VERIFIED else "UNVERIFIED (check console Billing > Prices)"
    print(f"Prices: {status}")
    print(f"{'model':<42}{'calls':>6}{'in':>9}{'out':>9}{'est $':>10}")
    total = 0.0
    for model, row in sorted(per.items()):
        total += row["cost"]
        note = f"  ({row['unpriced']} unpriced)" if row["unpriced"] else ""
        print(f"{model:<42}{row['calls']:>6}{row['in']:>9}{row['out']:>9}{row['cost']:>10.5f}{note}")
    print(f"{'TOTAL':<42}{'':>6}{'':>9}{'':>9}{total:>10.5f}")
    print(f"Tavily: {tav['searches']} searches, {tav['credits']} credits, "
          f"~${tav['est_usd']:.5f} (est)")
    if bad:
        print(f"Skipped {bad} malformed line(s).")

    super_price = PRICES.get("nvidia/nemotron-3-super-120b-a12b")
    if super_price:
        base = HERMES_BASELINE_IN * super_price[0] / 1_000_000
        print(f"Planning: one Hermes call on Super is about ${base:.4f} for the baseline input alone.")


if __name__ == "__main__":
    summary()
