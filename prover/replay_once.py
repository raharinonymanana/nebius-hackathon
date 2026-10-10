"""One-shot, model-free replay CLI over the sealed verification path.

Runs ONLY the engine's replay path (build_checkpoint -> submit_proof ->
proven_replays) and prints a single machine-readable JSON verdict line to
stdout. No model calls, no Tavily calls, no exploration -- so, like
eval_report.py, it does NOT touch costlog. It is the dependency for an MCP
server built next.

Run from the repo root:
    TARGET_SPEC_PATH=targets/ormar/spec.py TARGET_VARIANT=vulnerable \
        python -m prover.replay_once '<payload>'
    # or pipe the payload on stdin when argv[1] is absent.

stdout is exactly one JSON line. Human/debug notes go to stderr only.
Exit code: 0 when ok:true (whatever the verdict), non-zero when ok:false.
"""
import json
import os
import sys

import prover.agent_v4 as a


def _emit(obj, exit_code):
    """Write exactly one JSON line to stdout and exit with the given code."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def main():
    # --- inputs (argv + env) -------------------------------------------------
    spec_path = os.environ.get("TARGET_SPEC_PATH")
    if not spec_path:
        _emit({"ok": False, "error_type": "usage",
               "error": "TARGET_SPEC_PATH env var is required"}, 2)
    variant = os.environ.get("TARGET_VARIANT", "vulnerable")

    if len(sys.argv) > 1:
        payload = sys.argv[1]
    else:
        payload = sys.stdin.read()
    if not payload:
        _emit({"ok": False, "error_type": "usage",
               "error": "no payload: pass it as argv[1] or on stdin"}, 2)

    # --- mirror agent_v4 __main__ setup, minus the agent/model loop ----------
    try:
        a.SPEC = a.load_spec(spec_path)
    except Exception as exc:  # noqa: BLE001
        _emit({"ok": False, "error_type": "spec_load",
               "error": f"{type(exc).__name__}: {exc}"}, 1)
    a.VARIANT = variant

    try:
        a.CHECKPOINT = a.build_checkpoint()
    except BaseException as exc:  # build_checkpoint raises SystemExit on failure
        _emit({"ok": False, "error_type": "checkpoint",
               "error": f"{type(exc).__name__}: {exc}"}, 1)

    # --- the sealed replay path ----------------------------------------------
    try:
        result = a.submit_proof(payload)
    except Exception as exc:  # noqa: BLE001
        _emit({"ok": False, "error_type": "submit",
               "error": f"{type(exc).__name__}: {exc}"}, 1)
    if "error" in result:
        _emit({"ok": False, "error_type": "submit", "error": result["error"]}, 1)

    # Verdict comes STRICTLY from the same function the engine's verdict uses.
    proven = a.proven_replays()
    verdict = "PROVEN" if proven else "NOT PROVEN"

    _emit({
        "ok": True,
        "target": spec_path,
        "variant": variant,
        "payload_len": len(payload),
        "verdict": verdict,
        "leaked": result.get("leaked_secret"),
        "exit_code": result.get("exit_code"),
        "seconds": result.get("seconds"),
        "stderr": result.get("stderr", "")[:300],
    }, 0)


if __name__ == "__main__":
    main()
