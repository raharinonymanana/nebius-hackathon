"""Remediation loop: prove -> patch -> re-prove -> still-works -> one receipt.

A NEW layer ON TOP of the engine. The engine (prover/agent_v4.py) keeps its single
job; this module only orchestrates it: it sets agent_v4's module globals and calls its
existing primitives (build_checkpoint, run_agent, submit_proof, proven_replays). It
NEVER reimplements the harness or the replay — evidence comes only from submit_proof's
replay through SPEC.harness_code(). A second replay path would be a second, untrusted
evidence path, which is forbidden.

Verdict wording is scoped: "FIX VERIFIED" / "FIX NOT VERIFIED" means exactly "this
proven exploit is closed and benign use still works" on the patched build. It never
means "safe" or "secure".

For the Starlette cartridge the patch IS the dependency upgrade: the vulnerable build
pip-installs starlette==VULN_VERSION (0.26.1) and the fixed build pip-installs
FIXED_VERSION (0.27.0) via the engine's setup_commands hook.

Run from the repo root (spends ~1 model run, Phase A only):
    TARGET_SPEC_PATH=targets/starlette/spec.py python -m prover.remediate

Cartridge selection mirrors the live run, but defaults to the Starlette cartridge:
    TARGET_SPEC_PATH unset -> targets/starlette/spec.py
"""
import datetime
import json
import os

from prover import agent_v4 as a

# Cartridge selection, same env-var style as the live run; default = Starlette.
_DEFAULT_SPEC = os.path.join(a._REPO_ROOT, "targets", "starlette", "spec.py")
_spec_path = os.environ.get("TARGET_SPEC_PATH") or _DEFAULT_SPEC
a.SPEC = a.load_spec(_spec_path)


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_remediation_receipt(record):
    """Write receipts/<NAME>_remediation_<UTC>.json. A new remediation receipt, not an
    edit to any existing one and not the engine's own write_receipt format."""
    out_dir = os.path.join(a._REPO_ROOT, "receipts")
    os.makedirs(out_dir, exist_ok=True)
    stamp = record["utc"].replace(":", "").replace("-", "").replace(".", "")
    path = os.path.join(out_dir, f"{a.SPEC.NAME}_remediation_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)
    return path


def run():
    SPEC = a.SPEC
    print(f"Remediation loop: {SPEC.NAME}")
    print(f"  cartridge : {_spec_path}")
    print(f"  patch     : {getattr(SPEC, 'VULN_VERSION', '?')} -> "
          f"{getattr(SPEC, 'FIXED_VERSION', '?')} (dependency upgrade)")

    base_record = {
        "target": SPEC.NAME,
        "cve": getattr(SPEC, "CVE", None),
        "vulnerable_version": getattr(SPEC, "VULN_VERSION", None),
        "fixed_version": getattr(SPEC, "FIXED_VERSION", None),
        "canary": a.FLAG,
        "model": a.MODEL,
    }

    # ---- Phase A: PROVE on the vulnerable build (spends ~1 model run) ----------
    print("\n[Phase A] PROVE — vulnerable build, live agent run")
    a.VARIANT = "vulnerable"
    a.RECEIPTS.clear()
    a.REPLAYS.clear()
    a.CHECKPOINT = a.build_checkpoint()
    print(f"  checkpoint image: {getattr(a.CHECKPOINT, 'uuid', None)}")
    a.run_agent()

    proven = a.proven_replays()
    if not proven:
        print("\n[Phase A] NOT PROVEN — cannot verify a fix for an unproven vulnerability.")
        record = {
            **base_record,
            "utc": _utc_now(),
            "proven": False,
            "proven_payload": None,
            "exploit_closed": None,
            "still_works": None,
            "verdict": "FIX NOT VERIFIED (vulnerability not proven)",
        }
        path = write_remediation_receipt(record)
        print_summary(record)
        print(f"\nRemediation receipt: {os.path.relpath(path, a._REPO_ROOT)}")
        return record

    P = proven[0]["payload"]
    print(f"  PROVEN by replay {proven[0]['submit']} with payload {P!r}")

    # ---- Phase B: PATCH + RE-PROVE on the fixed build --------------------------
    print("\n[Phase B] PATCH + RE-PROVE — fixed build, replay the proven payload")
    a.VARIANT = "fixed"
    a.CHECKPOINT = a.build_checkpoint()  # installs FIXED_VERSION via setup_commands
    print(f"  patched checkpoint image: {getattr(a.CHECKPOINT, 'uuid', None)}")
    a.REPLAYS.clear()
    res_b = a.submit_proof(P)
    rec_b = a.REPLAYS[-1]
    exploit_closed = not rec_b["leaked"]
    print(f"  replay {P!r}: leaked={rec_b['leaked']} exit={rec_b['exit_code']} "
          f"-> exploit_closed={exploit_closed}")
    if "error" in res_b:
        print(f"  (submit_proof error: {res_b['error']})")

    # ---- Phase C: STILL-WORKS on the same patched build ------------------------
    print("\n[Phase C] STILL-WORKS — benign read on the patched build")
    res_c = a.submit_proof(SPEC.BENIGN_INPUT)
    rec_c = a.REPLAYS[-1]
    still_works = (rec_c["exit_code"] == 0 and not rec_c["leaked"])
    print(f"  replay {SPEC.BENIGN_INPUT!r}: exit={rec_c['exit_code']} "
          f"leaked={rec_c['leaked']} -> still_works={still_works}")
    if "error" in res_c:
        print(f"  (submit_proof error: {res_c['error']})")

    # ---- Phase D: RECEIPT + VERDICT --------------------------------------------
    fix_verified = bool(proven) and exploit_closed and still_works
    record = {
        **base_record,
        "utc": _utc_now(),
        "proven": True,
        "proven_payload": P,
        "exploit_closed": exploit_closed,
        "still_works": still_works,
        "verdict": "FIX VERIFIED" if fix_verified else "FIX NOT VERIFIED",
    }
    path = write_remediation_receipt(record)
    print_summary(record)
    print(f"\nRemediation receipt: {os.path.relpath(path, a._REPO_ROOT)}")
    return record


def print_summary(record):
    print("\n=== REMEDIATION SUMMARY (scoped: this proven exploit is closed and "
          "benign use still works) ===")
    print(f"  target            : {record['target']}")
    if record.get("cve"):
        print(f"  cve               : {record['cve']}")
    print(f"  patch             : {record['vulnerable_version']} -> "
          f"{record['fixed_version']}")
    print(f"  proven            : {record['proven']}  payload={record['proven_payload']!r}")
    print(f"  exploit_closed    : {record['exploit_closed']}")
    print(f"  still_works       : {record['still_works']}")
    print(f"  VERDICT           : {record['verdict']}")


if __name__ == "__main__":
    run()
