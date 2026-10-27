"""Offline fuzz test for the /api/verify INPUT-VALIDATION layer (demo/app.py).
Zero ConTree, zero network, zero model calls -- verify_service is STUBBED, so the
full handler can be fuzzed without ever reaching the live sandbox. Deterministic
(seeded). Two targets:

  1. _parse_verify_body -- hundreds of random / edge event bodies must NEVER raise,
     and must return a clean (target, input, error) triple: an error string on bad
     input, or (str, str, None) on good input.
  2. handler(POST /api/verify, ...) with the per-container speed bumps bypassed and
     verify_service stubbed -- any fuzzed body must return a well-formed HTTP
     response, NEVER a 500 / crash.

Property under test: hostile or malformed input is rejected cleanly and never
crashes the deployed handler.

Run from the repo root: python -m tests.fuzz_input_verify
"""
import base64
import json
import random
import sys
import types

# --- stub prover.verify_service BEFORE demo.app's lazy import reaches it ------
import prover  # empty package, cheap

def _fake_verify(target, user_input, *, timeout_s=25.0, base_image=None):
    return {"verdict": "NOT PROVEN", "mode": "handed", "input": user_input,
            "canary": "", "model": "none (stub)", "verification_is_model_free": True,
            "utc": "2026-01-01T00:00:00+00:00", "source_receipt": "stub.json",
            "note": "fuzz stub"}

_stub = types.ModuleType("prover.verify_service")
_stub.verify = _fake_verify
prover.verify_service = _stub
sys.modules["prover.verify_service"] = _stub

import demo.app as app  # noqa: E402
from demo.app import handler, _fake_event, _parse_verify_body, MAX_INPUT_LEN  # noqa: E402

random.seed(1234)  # deterministic fuzz corpus


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


def rand_str(n):
    pool = ("ABCabc012 \t\n\"'{}[]:,\\/()<>;=&%$#@!`~"
            "\x00\x7fé中\U0001f600")
    return "".join(random.choice(pool) for _ in range(n))


def nasty_bodies():
    """A fresh corpus of hostile / malformed / edge bodies each call."""
    fixed = [
        None, "", "not json", "{", "[]", "123", "true", "null", '"a string"',
        json.dumps({"target": "ormar"}),                       # no input
        json.dumps({"input": "x"}),                            # no target
        json.dumps({"target": "", "input": "x"}),              # empty target
        json.dumps({"target": 123, "input": "x"}),             # wrong type
        json.dumps({"target": "ormar", "input": 123}),         # wrong type
        json.dumps({"target": "ormar", "input": None}),
        json.dumps({"target": "ormar", "input": "A" * (MAX_INPUT_LEN + 1)}),  # oversize
        json.dumps({"target": "ormar", "input": "price"}),     # VALID -> stub
        json.dumps({"target": "ormar", "input": rand_str(50)}),
    ]
    for b in fixed:
        yield b
    for _ in range(300):
        pick = random.random()
        if pick < 0.3:
            yield rand_str(random.randint(0, 80))
        elif pick < 0.6:
            yield json.dumps({"target": rand_str(8),
                              "input": rand_str(random.randint(0, 40))})
        elif pick < 0.8:
            yield json.dumps({rand_str(4): rand_str(6)
                              for _ in range(random.randint(0, 4))})
        else:
            yield rand_str(random.randint(0, 20))


results = []

# --- target 1: _parse_verify_body never raises; returns a clean triple -------
parse_ok = True
for body in nasty_bodies():
    ev = {"body": body}
    if isinstance(body, str) and random.random() < 0.2:
        ev = {"body": base64.b64encode(body.encode()).decode(), "isBase64Encoded": True}
    try:
        t, ui, err = _parse_verify_body(ev)
    except Exception as e:  # noqa: BLE001
        print(f"  _parse_verify_body RAISED on {body!r}: {type(e).__name__}: {e}")
        parse_ok = False
        continue
    if err is not None:
        if not isinstance(err, str) or not err:
            print(f"  bad error shape on {body!r}: {err!r}")
            parse_ok = False
    else:
        if not (isinstance(t, str) and t and isinstance(ui, str)):
            print(f"  bad accepted triple on {body!r}: {(t, ui)!r}")
            parse_ok = False
results.append(check("1. _parse_verify_body never raises; returns a clean triple", parse_ok))

# --- target 2: full handler never 500s on a fuzzed verify body ---------------
# Bypass the per-container speed bumps so every body exercises the real
# parse/size/verify-guard path (not just the rate limiter).
app._rl_take = lambda: True
app._inflight_acquire = lambda: True
app._inflight_release = lambda: None

handler_ok = True
statuses = set()
for body in nasty_bodies():
    try:
        resp = handler(_fake_event("POST", "/api/verify", body), None)
    except Exception as e:  # noqa: BLE001
        print(f"  handler RAISED on {body!r}: {type(e).__name__}: {e}")
        handler_ok = False
        continue
    st = resp.get("statusCode")
    statuses.add(st)
    if st == 500:
        print(f"  handler 500 on {body!r}: {str(resp.get('body'))[:120]}")
        handler_ok = False
    if not (isinstance(resp.get("body"), str) and "statusCode" in resp):
        print(f"  malformed response on {body!r}: {resp!r}")
        handler_ok = False
results.append(check(
    f"2. handler never 500s / always well-formed (statuses seen: {sorted(s for s in statuses if s)})",
    handler_ok))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
