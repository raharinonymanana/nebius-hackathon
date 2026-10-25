"""Offline router checks for demo/app.py. Zero network, zero ConTree, zero model
calls -- the static router + /api/verify GUARDS only. Every case fails fast at
parse / size / method, BEFORE the lazy `from prover import verify_service`
import, so the live branch is never reached and nothing is installed. Promotes
the hand-run __main__ self-test into the automated suite so the deployed API's
guard surface is covered on every push.

Run from the repo root: python -m tests.app_router_verify
"""
import json
import sys

from demo.app import handler, _fake_event, MAX_INPUT_LEN


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


def resp_of(method, path, body=None):
    return handler(_fake_event(method, path, body), None)


results = []

# --- status-code contract for every router branch (all offline) --------------
# (label, method, path, body, expected). POSTs kept <= burst (5) so the
# per-container rate limiter does not trip during the deterministic checks.
cases = [
    ("1. GET / -> 200", "GET", "/", None, 200),
    ("2. GET /api/data -> 200", "GET", "/api/data", None, 200),
    ("3. GET /nope -> 404", "GET", "/nope", None, 404),
    ("4. GET /../app.py (traversal) -> 404", "GET", "/../app.py", None, 404),
    ("5. GET /api/verify (wrong method) -> 405", "GET", "/api/verify", None, 405),
    ("6. POST /api/verify (missing body) -> 400", "POST", "/api/verify", None, 400),
    ("7. POST /api/verify (invalid JSON) -> 400", "POST", "/api/verify", "not json", 400),
    ("8. POST /api/verify (no input) -> 400", "POST", "/api/verify",
     json.dumps({"target": "ormar"}), 400),
    ("9. POST /api/verify (oversize) -> 400", "POST", "/api/verify",
     json.dumps({"target": "ormar", "input": "A" * (MAX_INPUT_LEN + 1)}), 400),
]
for label, method, path, body, want in cases:
    results.append(check(label, resp_of(method, path, body)["statusCode"] == want))

# --- content guarantees the status code alone does not prove -----------------
root = resp_of("GET", "/")
results.append(check(
    "10. GET / is an html document",
    root["headers"]["Content-Type"].startswith("text/html")
    and "<!doctype html" in root["body"].lower()))

data = resp_of("GET", "/api/data")
results.append(check(
    "11. GET /api/data is JSON, schema_version 1",
    data["headers"]["Content-Type"] == "application/json"
    and json.loads(data["body"])["schema_version"] == 1))

# --- traversal is a real defence: must not leak app.py source (not just a 404) -
trav = resp_of("GET", "/../app.py")
results.append(check(
    "12. traversal response carries no app.py source",
    "def handler" not in trav["body"]))

# --- oversize rejected with a clean named error, never a stack trace ----------
over = resp_of("POST", "/api/verify",
               json.dumps({"target": "ormar", "input": "A" * (MAX_INPUT_LEN + 1)}))
results.append(check(
    "13. oversize -> clean 'input_too_large' error body",
    json.loads(over["body"]).get("error") == "input_too_large"))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
