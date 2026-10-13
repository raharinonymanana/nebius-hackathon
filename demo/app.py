"""AWS Lambda handler for the prove-it demo, served behind a Function URL.

The STATIC router (GET /, /api/data, /assets/*) is pure Python standard library
only -- NO third-party imports, NO model / API / network / priced call -- it
just reads files that sit beside it at deploy time and returns them.

The ONE live branch, POST /api/verify, lazily imports prover.verify_service
(which uses the ConTree SDK) only when a verify request arrives, so the static
router stays importable and network-free even where the SDK is absent. The live
path degrades gracefully: on timeout / ConTree error it returns a valid
NOT-PROVEN JSON, never a 500, so the gallery page keeps working.

Function URL events are payload format v2. The handler always returns the shape
{"statusCode", "headers", "body", "isBase64Encoded"} with body as a string.

Local self-test (no network):   python -m demo.app
Live verify self-test (ConTree): PROVE_IT_LIVE=1 PROVE_IT_BASE_IMAGE=prove-it-ormar-base \
                                 python -m demo.app
"""
import base64
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))

# Compiled React UI (Vite build) is copied here at deploy time: demo/web/.
WEB = Path(BASE) / "web"

# Maps a file suffix to the Content-Type we serve it with.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}

# Shown when the UI has not been built/deployed yet, so the router is testable
# before the real demo shell exists.
INDEX_FALLBACK = (
    "<!doctype html><meta charset=utf-8><title>prove-it</title>"
    "<p>demo shell pending. API is live: <a href=/api/data>/api/data</a></p>"
)

# --- /api/verify policy ------------------------------------------------------
# Mirrors prover.verify_service.MAX_INPUT_LEN; enforced here too (defense in
# depth) so an oversize body is rejected BEFORE we import/call the SDK.
MAX_INPUT_LEN = 2000

# PER-CONTAINER speed bumps ONLY. Both reset on cold start and are process-local
# (one Lambda execution environment). They are NOT the global DoS guard -- the
# real cap is Lambda RESERVED CONCURRENCY, set on the function in 3b-iii. Do not
# mistake these for a global limit: 100 warm containers = 100x these numbers.
MAX_INFLIGHT = 3                         # concurrent verifies allowed in THIS container
_RL_RATE = 1.0                           # sustained ~1 req/sec (token refill per second)
_RL_BURST = 5.0                          # small burst bucket

_inflight = 0
_inflight_lock = threading.Lock()

_rl_lock = threading.Lock()
_rl_tokens = _RL_BURST
_rl_last = time.monotonic()


def _rl_take():
    """Per-container token bucket. True if a token was available (request may
    proceed), False if the bucket is exhausted (429). Speed-bump only."""
    global _rl_tokens, _rl_last
    with _rl_lock:
        now = time.monotonic()
        _rl_tokens = min(_RL_BURST, _rl_tokens + (now - _rl_last) * _RL_RATE)
        _rl_last = now
        if _rl_tokens >= 1.0:
            _rl_tokens -= 1.0
            return True
        return False


def _inflight_acquire():
    """Per-container concurrency guard. True if a slot was taken (caller MUST
    release it in a finally), False if MAX_INFLIGHT already in flight (429)."""
    global _inflight
    with _inflight_lock:
        if _inflight >= MAX_INFLIGHT:
            return False
        _inflight += 1
        return True


def _inflight_release():
    global _inflight
    with _inflight_lock:
        _inflight -= 1


def _parse_verify_body(event):
    """Return (target, user_input, error). error is a client-facing string when
    the body is missing/invalid; never raises, never leaks a stack trace."""
    raw = event.get("body")
    if raw is None or raw == "":
        return None, None, "missing request body"
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except Exception:  # noqa: BLE001
            return None, None, "body is not valid base64 utf-8"
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None, None, "body is not valid JSON"
    if not isinstance(data, dict):
        return None, None, "body must be a JSON object"
    target = data.get("target")
    user_input = data.get("input")
    if not isinstance(target, str) or not target:
        return None, None, "'target' (non-empty string) is required"
    if not isinstance(user_input, str):
        return None, None, "'input' (string) is required"
    return target, user_input, None


def _degraded_not_proven(user_input, reason):
    """A valid NOT-PROVEN contract receipt for when the live path is
    unavailable (import/SDK failure). Keeps the page working -- never a 500."""
    utc = datetime.now(timezone.utc).isoformat()
    return {
        "verdict": "NOT PROVEN",
        "mode": "handed",
        "input": user_input,
        "canary": "",
        "model": "none (model-free replay)",
        "verification_is_model_free": True,
        "utc": utc,
        "source_receipt": "ormar-aggregate-sql-injection_live_degraded.json",
        "note": reason,
    }


def _handle_verify(event):
    """POST /api/verify: guards -> parse -> size cap -> verify_service. Returns a
    _response(). Degrades to NOT-PROVEN JSON on timeout/SDK error, 400 on bad
    input, 429 on per-container limits. Never 500s the live path."""
    if not _rl_take():
        return _response(429, "application/json", json.dumps(
            {"error": "rate_limited", "detail": "per-container rate limit; retry shortly"}))
    if not _inflight_acquire():
        return _response(429, "application/json", json.dumps(
            {"error": "too_many_inflight",
             "detail": f"per-container concurrency limit ({MAX_INFLIGHT}) reached"}))
    try:
        target, user_input, err = _parse_verify_body(event)
        if err:
            return _response(400, "application/json", json.dumps(
                {"error": "bad_request", "detail": err}))
        if len(user_input) > MAX_INPUT_LEN:
            return _response(400, "application/json", json.dumps(
                {"error": "input_too_large",
                 "detail": f"input exceeds {MAX_INPUT_LEN} chars"}))

        base_image = os.environ.get("PROVE_IT_BASE_IMAGE", "prove-it-ormar-base")
        try:
            from prover import verify_service
            result = verify_service.verify(
                target, user_input, timeout_s=8.0, base_image=base_image)
        except ValueError as ve:  # whitelist / type reject -> client error
            return _response(400, "application/json", json.dumps(
                {"error": "rejected", "detail": str(ve)}))
        except Exception as ex:  # noqa: BLE001 -- degrade, never 500 the live path
            result = _degraded_not_proven(
                user_input, f"verification unavailable: {type(ex).__name__}: {ex}")
        return _response(200, "application/json", json.dumps(result))
    finally:
        _inflight_release()


def _response(status, content_type, body):
    """Build the Function URL v2 response shape. body is always a string."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": content_type},
        "body": body,
        "isBase64Encoded": False,
    }


def _read(filename):
    """Read a file beside this handler as text."""
    with open(os.path.join(BASE, filename), encoding="utf-8") as f:
        return f.read()


def _serve_web(path):
    """Serve a static file from demo/web for a GET path, or None if absent.

    Resolves the requested path and confirms it stays inside demo/web, so a
    traversal like /../app.py cannot escape the build directory.
    """
    rel = path.lstrip("/") or "index.html"
    target = (WEB / rel).resolve()
    try:
        target.relative_to(WEB.resolve())
    except ValueError:
        return None  # escaped demo/web -> treat as not found
    if not target.is_file():
        return None
    content_type = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
    return _response(200, content_type, target.read_text(encoding="utf-8"))


def handler(event, context):
    event = event or {}
    path = event.get("rawPath", "/") or "/"
    method = (event.get("requestContext", {}) or {}).get("http", {}).get("method", "GET")

    try:
        # 1. GET "/" -> the compiled UI (or an inline fallback if not built yet)
        if path == "/" and method == "GET":
            served = _serve_web("index.html")
            if served is not None:
                return served
            return _response(200, "text/html; charset=utf-8", INDEX_FALLBACK)

        # 2. GET "/api/data" -> the frozen data contract, verbatim file text
        if path == "/api/data" and method == "GET":
            try:
                body = _read("demo_data.json")
            except FileNotFoundError:
                return _response(
                    500, "application/json",
                    json.dumps({"error": "data_missing",
                                "detail": "demo_data.json not found"}),
                )
            return _response(200, "application/json", body)

        # 3. "/api/verify" -> live, model-free verification over ConTree (POST only)
        if path == "/api/verify":
            if method != "POST":
                return _response(
                    405, "application/json",
                    json.dumps({"error": "method_not_allowed", "detail": "POST only"}),
                )
            return _handle_verify(event)

        # 4. any other GET -> a static file under demo/web (assets, favicon, ...)
        if method == "GET":
            served = _serve_web(path)
            if served is not None:
                return served

        # 5. anything else
        return _response(
            404, "application/json",
            json.dumps({"error": "not_found", "path": path}),
        )
    except Exception as exc:  # noqa: BLE001 -- never throw; return a 500 json body
        return _response(
            500, "application/json",
            json.dumps({"error": "internal_error", "detail": str(exc)}),
        )


def _fake_event(method, path, body=None):
    """Build a minimal Function URL v2 event for local testing."""
    event = {"rawPath": path, "requestContext": {"http": {"method": method}}}
    if body is not None:
        event["body"] = body
    return event


if __name__ == "__main__":
    # --- router self-test: NO network (none of these reach verify_service) ---
    # (label, method, path, body, expected_status). Keep POSTs <= burst so the
    # per-container rate limiter does not trip during the deterministic checks.
    cases = [
        ("GET /", "GET", "/", None, 200),
        ("GET /api/data", "GET", "/api/data", None, 200),
        ("GET /nope", "GET", "/nope", None, 404),
        ("GET /../app.py (traversal)", "GET", "/../app.py", None, 404),
        ("GET /api/verify (wrong method)", "GET", "/api/verify", None, 405),
        ("POST /api/verify (missing body)", "POST", "/api/verify", None, 400),
        ("POST /api/verify (invalid JSON)", "POST", "/api/verify", "not json", 400),
        ("POST /api/verify (no input)", "POST", "/api/verify",
         json.dumps({"target": "ormar"}), 400),
        ("POST /api/verify (oversize)", "POST", "/api/verify",
         json.dumps({"target": "ormar", "input": "A" * (MAX_INPUT_LEN + 1)}), 400),
    ]
    for label, method, path, body, want in cases:
        resp = handler(_fake_event(method, path, body), None)
        got = resp["statusCode"]
        flag = "OK" if got == want else "MISMATCH"
        print(f"{label} -> {got} [{flag}, want {want}] ({len(resp['body'])} bytes)")
        assert got == want, f"{label}: got {got}, want {want}"

    # GET "/" is a real html document; /api/data is schema v1
    root_resp = handler(_fake_event("GET", "/"), None)
    assert root_resp["headers"]["Content-Type"].startswith("text/html")
    assert "<!doctype html" in root_resp["body"].lower()
    assert json.loads(handler(_fake_event("GET", "/api/data"), None)["body"])["schema_version"] == 1
    print("router self-test OK (static + /api/verify guards, no network)")

    # --- live verify path: ConTree, only when explicitly enabled ------------
    if os.environ.get("PROVE_IT_LIVE") == "1":
        print("\n--- live verify (ConTree; base_image="
              f"{os.environ.get('PROVE_IT_BASE_IMAGE', 'prove-it-ormar-base')}) ---")
        EXPLOIT = "(SELECT password_hash FROM users WHERE username='admin')"
        for label, payload in [("exploit", EXPLOIT), ("benign", "price")]:
            body = json.dumps({"target": "ormar", "input": payload})
            t0 = time.monotonic()
            resp = handler(_fake_event("POST", "/api/verify", body), None)
            dt = time.monotonic() - t0
            doc = json.loads(resp["body"])
            print(f"\nPOST /api/verify ({label}) -> {resp['statusCode']}  {dt:.2f}s")
            print(json.dumps(doc, indent=2))
