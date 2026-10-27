"""LIVE security-boundary suite for the DEPLOYED verify path
(prover/verify_service.py). SPENDS ConTree compute (bakes ormar 0.22.0 once via
ensure_image(), then a few disposable replays). NO model calls -> zero
Nemotron/Tavily credits. NOT run in CI (needs live ConTree + a real
NEBIUS_API_KEY in .env).

Drives the real verify() through its public boundary as PASS/FAIL:
  1. exploit                -> PROVEN
  2. benign                 -> NOT PROVEN
  3. oversized (>cap)       -> ValueError (rejected before any sandbox work)
  4. non-whitelist target   -> ValueError
  5. shell-metachar payload -> NOT PROVEN, no crash (input is DATA, never shell)

On a clean pass it writes a suite-summary to receipts/suites/ (a subdir, so
prover.eval_report -- which globs receipts/*.json only -- never scans it: this
is suite evidence, not a per-run receipt).

Run from the repo root with the venv active:
    python -m tests.verify_service_security
"""
import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()  # verify_service does not load .env itself; the live path needs the key

from prover import verify_service as vs

EXPLOIT = vs.SPEC.EXPLOIT_INPUT
BENIGN = vs.SPEC.BENIGN_INPUT
CAP = vs.MAX_INPUT_LEN


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


results = []

# 1. real exploit -> PROVEN
r = vs.verify("ormar", EXPLOIT)
results.append(check("1. exploit -> PROVEN", r.get("verdict") == "PROVEN"))

# 2. benign field -> NOT PROVEN
r = vs.verify("ormar", BENIGN)
results.append(check("2. benign -> NOT PROVEN", r.get("verdict") == "NOT PROVEN"))

# 3. oversized input -> ValueError BEFORE any sandbox work (size cap)
try:
    vs.verify("ormar", "A" * (CAP + 1))
    results.append(check("3. oversized -> ValueError (size cap)", False))
except ValueError:
    results.append(check("3. oversized -> ValueError (size cap)", True))

# 4. non-whitelisted target -> ValueError (never runs an arbitrary target)
try:
    vs.verify("starlette", EXPLOIT)
    results.append(check("4. non-whitelist target -> ValueError", False))
except ValueError:
    results.append(check("4. non-whitelist target -> ValueError", True))

# 5. shell metacharacters in the payload -> NOT PROVEN, no crash. The input is
#    delivered to the sandbox as a FILE and read as data (the aggregate field
#    name), never interpolated into the shell command, so it cannot execute.
SHELL_META = "price; echo PWNED > /app/pwned.txt"
r = vs.verify("ormar", SHELL_META)
results.append(check("5. shell-metachar payload -> NOT PROVEN (input is data, not shell)",
                     r.get("verdict") == "NOT PROVEN"))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")

if passed == len(results):
    utc = datetime.now(timezone.utc).isoformat()
    stamp = utc.replace(":", "").replace("-", "").replace(".", "")
    summary = {
        "suite": "verify_service security boundary",
        "target": vs.WHITELIST[0],
        "cases_passed": passed,
        "cases_total": len(results),
        "max_input_len": vs.MAX_INPUT_LEN,
        "boundary_properties": [
            "target whitelist (non-whitelist -> ValueError)",
            "input size cap (oversized -> ValueError)",
            "canary-only verdict (exploit PROVEN / benign NOT PROVEN)",
            "input delivered as data, not shell (metachars inert -> NOT PROVEN)",
        ],
        "model_calls": 0,
        "verification_is_model_free": True,
        "utc": utc,
        "note": ("verify() proves the exploit and rejects benign, oversized, "
                 "non-whitelist, and shell-metachar inputs; no model in the path."),
    }
    out_dir = os.path.join(vs._REPO, "receipts", "suites")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"verify_service_security_{stamp}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"suite summary: {os.path.relpath(out, vs._REPO)}")

sys.exit(0 if passed == len(results) else 1)
