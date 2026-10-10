"""FastMCP server 'prove-it-verifier' over the sealed replay path.

Exposes exactly two tools (list_targets, verify_proof). The sealed engine is
reached ONLY by shelling out to replay_once.py in a fresh subprocess per call,
so no module-global state can bleed between calls. The server makes ZERO
model/Tavily calls, so there is no costlog here.

Security boundary: verify_proof accepts only a target NAME from the TARGETS
whitelist (built by scanning targets/ at import). A caller can never pass a
filesystem path or make the server load an arbitrary spec.py -- load_spec() in
agent_v4 does exec_module(), so an unknown path would be arbitrary code
execution. The whitelist closes that.

Pinned SDK: we are on mcp<2, so the import is
    from mcp.server.fastmcp import FastMCP
NOT  from fastmcp import ...  (that is the 2.x package we do not have).
"""
import json
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

# repo root = parent of the prover/ dir that holds this file.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TARGETS_DIR = os.path.join(_REPO_ROOT, "targets")

VALID_VARIANTS = ["vulnerable", "fixed"]


def _build_targets():
    """Whitelist: each targets/<name>/ that holds a spec.py -> its spec path."""
    out = {}
    if os.path.isdir(_TARGETS_DIR):
        for name in os.listdir(_TARGETS_DIR):
            spec = os.path.join(_TARGETS_DIR, name, "spec.py")
            if os.path.isfile(spec):
                out[name] = spec
    return out


TARGETS = _build_targets()

mcp = FastMCP("prove-it-verifier")


def _scrub_reason(stderr: str) -> str:
    """Most informative exception line from stderr, with internal paths stripped
    to basenames so an external caller sees WHY without our filesystem layout."""
    if not stderr:
        return ""
    lines = [ln for ln in stderr.splitlines() if ln.strip()]
    chosen = ""
    for ln in reversed(lines):
        stripped = ln.strip()
        # an exception line looks like "<ErrorClass>: <msg>"
        head = stripped.split(":", 1)[0]
        if ": " in stripped and head and head[0].isalpha() and " " not in head:
            chosen = stripped
            break
    if not chosen:
        return ""
    # strip repo root, then collapse any absolute /app/... path to its basename.
    chosen = chosen.replace(_REPO_ROOT + os.sep, "").replace(_REPO_ROOT, "")
    out, i = [], 0
    while i < len(chosen):
        if chosen.startswith("/app/", i):
            j = i
            while j < len(chosen) and chosen[j] not in (" ", "'", '"', ",", ")"):
                j += 1
            out.append(os.path.basename(chosen[i:j]))
            i = j
        else:
            out.append(chosen[i])
            i += 1
    return "".join(out)


def _list_targets_impl() -> dict:
    return {"targets": sorted(TARGETS.keys()), "variants": list(VALID_VARIANTS)}


def _verify_proof_impl(target: str, variant: str = "vulnerable",
                       payload: str = "") -> dict:
    # --- validation (whitelist first, before touching anything) --------------
    if target not in TARGETS:
        return {"ok": False, "error_type": "unknown_target",
                "error": f"unknown target {target!r}",
                "valid_targets": sorted(TARGETS.keys())}
    if variant not in VALID_VARIANTS:
        return {"ok": False, "error_type": "bad_variant",
                "error": f"unknown variant {variant!r}",
                "valid_variants": list(VALID_VARIANTS)}
    if not payload or not isinstance(payload, str):
        return {"ok": False, "error_type": "usage",
                "error": "payload must be a non-empty string"}

    # --- fresh subprocess per call (payload as a list arg, no shell) ---------
    cmd = [sys.executable, "-m", "prover.replay_once", payload]
    env = dict(os.environ)
    env["TARGET_SPEC_PATH"] = TARGETS[target]
    env["TARGET_VARIANT"] = variant
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=120, cwd=_REPO_ROOT, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error_type": "timeout",
                "error": "replay exceeded 120s"}

    # parse the LAST non-empty stdout line as JSON (replay_once prints one line).
    parsed = None
    for ln in reversed((proc.stdout or "").splitlines()):
        if ln.strip():
            try:
                parsed = json.loads(ln)
            except json.JSONDecodeError:
                parsed = None
            break
    if parsed is None:
        return {"ok": False, "error_type": "replay_error",
                "error": (proc.stderr or "")[:300]}

    if not parsed.get("ok"):
        return parsed  # replay_once's own typed error, passed through.

    verdict = parsed.get("verdict")
    reason = "" if verdict == "PROVEN" else _scrub_reason(parsed.get("stderr", ""))
    return {"ok": True, "target": target, "variant": variant,
            "verdict": verdict, "leaked": parsed.get("leaked"),
            "exit_code": parsed.get("exit_code"), "seconds": parsed.get("seconds"),
            "reason": reason}


@mcp.tool()
def list_targets() -> dict:
    """List the verifiable targets (whitelist) and the valid variants."""
    return _list_targets_impl()


@mcp.tool()
def verify_proof(target: str, variant: str = "vulnerable", payload: str = "") -> dict:
    """Replay a payload against a whitelisted target/variant via the sealed
    engine and return a PROVEN / NOT PROVEN verdict (or a typed honest error)."""
    return _verify_proof_impl(target, variant, payload)


if __name__ == "__main__":
    mcp.run()  # stdio transport (FastMCP default)
