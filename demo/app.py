"""AWS Lambda handler for the prove-it demo, served behind a Function URL.

Pure Python standard library (json, os) only -- NO third-party imports and NO
model / API / network / priced call of any kind. This handler only reads files
that sit beside it at deploy time (demo_data.json, index.html) and returns them.

Function URL events are payload format v2. The handler always returns the shape
{"statusCode", "headers", "body", "isBase64Encoded"} with body as a string.

Local self-test (no network):  python -m demo.app
"""
import json
import os
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

        # 3. POST "/api/verify" -> deliberate stub seam (not wired yet)
        if path == "/api/verify" and method == "POST":
            return _response(
                501, "application/json",
                json.dumps({"error": "not_implemented",
                            "detail": "live verification seam - not wired yet"}),
            )

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


def _fake_event(method, path):
    """Build a minimal Function URL v2 event for local testing."""
    return {"rawPath": path, "requestContext": {"http": {"method": method}}}


if __name__ == "__main__":
    cases = [
        ("GET", "/"),
        ("GET", "/api/data"),
        ("POST", "/api/verify"),
        ("GET", "/nope"),
        ("GET", "/../app.py"),  # traversal attempt -> must be 404
    ]
    for method, path in cases:
        resp = handler(_fake_event(method, path), None)
        print(f"{method} {path} -> {resp['statusCode']} ({len(resp['body'])} bytes)")

    # GET "/" -> the compiled index.html (when built into demo/web/)
    root_resp = handler(_fake_event("GET", "/"), None)
    assert root_resp["statusCode"] == 200, "GET / should be 200"
    assert root_resp["headers"]["Content-Type"].startswith("text/html"), "GET / html"
    assert "<!doctype html" in root_resp["body"].lower(), "GET / returns html document"
    print("GET / OK (html)")

    # GET "/api/data" -> the frozen contract, schema v1
    data_resp = handler(_fake_event("GET", "/api/data"), None)
    assert data_resp["statusCode"] == 200, "api/data should be 200"
    parsed = json.loads(data_resp["body"])
    assert parsed["schema_version"] == 1, "api/data schema_version should be 1"
    print("api/data OK")

    # Traversal must not escape demo/web
    trav_resp = handler(_fake_event("GET", "/../app.py"), None)
    assert trav_resp["statusCode"] == 404, "traversal should be 404"
    print("traversal blocked OK")
