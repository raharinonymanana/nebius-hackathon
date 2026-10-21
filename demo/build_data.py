"""Freeze the demo data contract: demo/demo_data.json (schema v1).

Deterministic and MODEL-FREE. This script reads only JSON on disk
(receipts/*.json via prover.eval_report, plus the hand-picked representative
receipt for each target/slot) and reuses prover.eval_report for every computed
number -- it never re-derives a Wilson interval, a cost, or a verdict, and it
never makes a model / API / Tavily / priced call of any kind.

Run from the repo root:  python -m demo.build_data

Honesty invariants baked in here (do not relax):
  * Verdicts are copied verbatim from the receipts; only PROVEN / NOT PROVEN /
    FIX VERIFIED ever appear.
  * `mode` is derived from the receipt itself: a run is "unaided" only when it
    ran in locate mode AND the receipt records located_unaided=true; everything
    else is "handed". Handed runs expose the vulnerable sink by design and are
    never labelled discovery/unaided.
  * `verification_is_model_free` describes the sealed REPLAY harness, not the
    original run. Each run keeps its real `model`; we never claim the run itself
    was model-free.
  * Target cards cover starlette / gitpython / ormar only. `seeded` stays out of
    the cards but its eval rows stay in (they come straight from eval_report).
"""
import datetime as _dt
import json
import os

from prover import eval_report

OUT_PATH = os.path.join("demo", "demo_data.json")
RECEIPTS_DIR = "receipts"
SCHEMA_VERSION = 1

VALID_VERDICTS = {"PROVEN", "NOT PROVEN", "FIX VERIFIED"}

# Target cards, in demo order. seeded is intentionally absent (not a card).
TARGET_ORDER = [
    "starlette-staticfiles-traversal",
    "gitpython-clone-ext-injection",
    "ormar-aggregate-sql-injection",
]

# Static, human-written classification of each known target. Not a computed
# metric -- a label describing the CVE class, kept consistent with the names.
CARD_META = {
    "starlette-staticfiles-traversal": {
        "name": "Starlette StaticFiles path traversal",
        "exploit_class": "path traversal",
    },
    "gitpython-clone-ext-injection": {
        "name": "GitPython clone ext:: command injection",
        "exploit_class": "command injection (ext:: transport)",
    },
    "ormar-aggregate-sql-injection": {
        "name": "ormar aggregate SQL injection",
        "exploit_class": "SQL injection (aggregate min/max)",
    },
}

# The single representative receipt chosen for each (target, slot). A null slot
# means no receipt of that kind exists on disk; see ORMAR note in eval.notes.
REPRESENTATIVE = {
    "starlette-staticfiles-traversal": {
        "proven": "starlette-staticfiles-traversal_vulnerable_20261009T063141110461+0000.json",
        "not_proven": "starlette-staticfiles-traversal_fixed_20261006T041025544538+0000.json",
        "fix_verified": "starlette-staticfiles-traversal_remediation_20261006T051332606246+0000.json",
    },
    "gitpython-clone-ext-injection": {
        "proven": "gitpython-clone-ext-injection_vulnerable_20261007T174209847855+0000.json",
        "not_proven": "gitpython-clone-ext-injection_fixed_20261007T174327594793+0000.json",
        "fix_verified": "gitpython-clone-ext-injection_remediation_20261008T153053306733+0000.json",
    },
    "ormar-aggregate-sql-injection": {
        "proven": "ormar-aggregate-sql-injection_vulnerable_20261009T173733161906+0000.json",
        "not_proven": None,  # no standalone fixed/NOT PROVEN receipt on disk
        "fix_verified": "ormar-aggregate-sql-injection_remediation_20261009T175028463864+0000.json",
    },
}

ORMAR_NOTE = (
    "ormar has no standalone fixed/NOT-PROVEN receipt on disk; its negative "
    "control is implicit in the FIX VERIFIED remediation run (exploit_closed=true "
    "against 0.23.0). A dedicated ormar fixed NOT-PROVEN receipt is pending."
)


def load_receipt(filename):
    """Read one receipt by filename from receipts/. JSON only, no side effects."""
    with open(os.path.join(RECEIPTS_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def run_mode(receipt):
    """Derive unaided vs handed from the receipt (never from assumption).

    Unaided only when the run was a locate run AND the harness recorded that the
    model located the vulnerable sink on its own. Everything else is handed.
    """
    effective = receipt.get("task_mode_effective") or receipt.get("task_mode")
    locate = receipt.get("locate") or {}
    if effective == "locate" and locate.get("located_unaided"):
        return "unaided"
    return "handed"


def run_input(receipt, slot):
    """The attacker-controlled input this run fed to the target, or None.

    proven       -> the payload the harness marked as the proving submit.
    fix_verified -> the proven_payload replayed against the patched version.
    not_proven   -> the first payload actually submitted (None if the run only
                    explored and never submitted a replay).
    """
    if slot == "fix_verified":
        return receipt.get("proven_payload")
    replays = receipt.get("replays_only_evidence") or []
    if slot == "proven":
        pb = receipt.get("proven_by")
        if isinstance(pb, int) and 1 <= pb <= len(replays):
            return replays[pb - 1].get("payload")
        for r in replays:
            if r.get("leaked"):
                return r.get("payload")
        return None
    # not_proven
    return replays[0].get("payload") if replays else None


def build_human_trace(receipt):
    """Plain-English steps rebuilt from a PROVEN receipt's own fields.

    Every step is sourced from a recorded field; exploration is explicitly
    flagged as non-evidence, and the verdict line credits only the harness.
    """
    steps = []
    adv = receipt.get("advisory") or {}
    if adv.get("cve"):
        steps.append(
            f"Advisory lookup: {adv['cve']} (fixed in {adv.get('fixed_version', '?')}) "
            f"- context only, never evidence."
        )
    locate = receipt.get("locate") or {}
    fn = locate.get("target_function")
    if locate.get("located_unaided"):
        steps.append(
            f"Located the vulnerable sink `{fn}` unaided - the advisory did not name it."
        )
    elif fn:
        steps.append(
            f"Handed mode: the vulnerable sink `{fn}` was supplied as the entry point "
            f"(advisory_named_function={bool(locate.get('advisory_named_function'))})."
        )
    k = len(receipt.get("exploration_runs_not_evidence") or [])
    if k:
        steps.append(
            f"Ran {k} sandbox exploration probe(s) to shape the payload - "
            f"exploration stdout is never evidence."
        )
    replays = receipt.get("replays_only_evidence") or []
    pb = receipt.get("proven_by")
    if isinstance(pb, int) and 1 <= pb <= len(replays):
        rp = replays[pb - 1]
        steps.append(
            f"Submitted exploit input to the sealed replay harness "
            f"(submit #{rp.get('submit', pb)}): {rp.get('payload')}"
        )
        steps.append(
            f"Harness observed the canary {receipt.get('canary')} in the target "
            f"output (leaked=true)."
        )
    steps.append("Verdict: PROVEN - confirmed solely by the model-free replay harness.")
    return steps


def build_advisory(receipt):
    """Trim the receipt's Tavily advisory for the UI. JSON only, no calls.

    Surfaces what the harness ALREADY captured at run time: the CVE, the fixed
    version, the single highest-scored cited advisory source, and how many
    sources were discarded as non-advisory. Returns None when no advisory block
    exists. Makes no model/API/Tavily call -- it only reshapes on-disk data, so
    build_data.py stays deterministic and free.
    """
    adv = receipt.get("advisory") or {}
    if not adv.get("cve"):
        return None
    # cited_sources arrive score-ranked; keep the top one with a real title +
    # score (constructed nvd/cve.org entries carry neither).
    top = None
    for s in adv.get("cited_sources") or []:
        if s.get("title") and s.get("score") is not None:
            top = {"url": s.get("url"), "title": s.get("title"), "score": s.get("score")}
            break
    return {
        "provider": adv.get("provider"),
        "cve": adv.get("cve"),
        "fixed_version": adv.get("fixed_version"),
        "top_source": top,
        "discarded_count": len(adv.get("discarded_sources") or []),
    }


def build_run(receipt, filename, slot):
    """Assemble one run dict for a target card from its representative receipt."""
    run = {
        "verdict": receipt.get("verdict"),
        "mode": run_mode(receipt),
        "input": run_input(receipt, slot),
        "canary": receipt.get("canary"),
        "model": receipt.get("model"),
        # The sealed replay harness is model-free; the run itself used `model`.
        "verification_is_model_free": True,
        "utc": receipt.get("utc"),
        "source_receipt": filename,
    }
    if slot == "proven":
        run["human_trace"] = build_human_trace(receipt)
        advisory = build_advisory(receipt)
        if advisory is not None:
            run["advisory"] = advisory
    if slot == "fix_verified":
        run["exploit_closed"] = receipt.get("exploit_closed")
        run["still_works"] = receipt.get("still_works")
    return run


def build_target_card(target_id):
    """Build one target card: metadata + the proven/not_proven/fix_verified runs."""
    slots = REPRESENTATIVE[target_id]
    proven_rcpt = load_receipt(slots["proven"])
    fix_rcpt = load_receipt(slots["fix_verified"])

    # CVE / versions: prefer the remediation receipt (it carries them explicitly),
    # falling back to the proven run's advisory block for a missing field.
    adv = proven_rcpt.get("advisory") or {}
    cve = fix_rcpt.get("cve") or adv.get("cve")
    vulnerable_version = fix_rcpt.get("vulnerable_version")
    fixed_version = fix_rcpt.get("fixed_version") or adv.get("fixed_version")

    runs = {
        "proven": build_run(proven_rcpt, slots["proven"], "proven"),
        "not_proven": None,
        "fix_verified": build_run(fix_rcpt, slots["fix_verified"], "fix_verified"),
    }
    if slots["not_proven"] is not None:
        np_rcpt = load_receipt(slots["not_proven"])
        runs["not_proven"] = build_run(np_rcpt, slots["not_proven"], "not_proven")

    meta = CARD_META[target_id]
    return {
        "id": target_id,
        "name": meta["name"],
        "cve": cve,
        "exploit_class": meta["exploit_class"],
        "vulnerable_version": vulnerable_version,
        "fixed_version": fixed_version,
        "runs": runs,
    }


def validate(data):
    """Honesty / integrity gate run on write. Raises AssertionError on violation."""
    for card in data["targets"]:
        runs = card["runs"]
        # proven + fix_verified are mandatory; not_proven may be null (see ORMAR_NOTE).
        assert runs.get("proven") is not None, f"{card['id']}: missing proven run"
        assert runs.get("fix_verified") is not None, f"{card['id']}: missing fix_verified run"
        assert "not_proven" in runs, f"{card['id']}: not_proven key absent"

        assert runs["proven"]["verdict"] == "PROVEN", f"{card['id']}: proven verdict wrong"
        assert runs["fix_verified"]["verdict"] == "FIX VERIFIED", \
            f"{card['id']}: fix_verified verdict wrong"
        if runs["not_proven"] is not None:
            assert runs["not_proven"]["verdict"] == "NOT PROVEN", \
                f"{card['id']}: non-null not_proven must be NOT PROVEN"

        for slot, run in runs.items():
            if run is None:
                continue
            assert run["verdict"] in VALID_VERDICTS, \
                f"{card['id']}/{slot}: illegal verdict {run['verdict']!r}"
            assert run["mode"] in ("unaided", "handed"), \
                f"{card['id']}/{slot}: illegal mode {run['mode']!r}"

    # The assembled JSON must round-trip.
    json.loads(json.dumps(data))


def build():
    """Assemble the full schema-v1 contract and return it as a dict."""
    valid, excluded = eval_report.load_receipts()
    metrics = eval_report.compute(valid)
    cost = eval_report.cost_totals()
    table = eval_report.collect_rows(metrics)

    notes = list(table["notes"])
    notes.append(ORMAR_NOTE)

    # eval_report pads the remediation note with leading spaces so it aligns under
    # the target column in the terminal; that alignment is meaningless in a data
    # contract, so drop it here (the printed table keeps its padding untouched).
    remediation = []
    for entry in table["remediation"]:
        entry = dict(entry)
        if entry.get("note"):
            entry["note"] = entry["note"].strip()
        remediation.append(entry)

    meta = {
        "model_cost_usd": (cost or {}).get("model_usd", 0.0),
        "model_calls": (cost or {}).get("model_calls", 0),
        "tavily_credits": (cost or {}).get("tav_credits", 0),
        "receipts_valid": len(valid),
        "receipts_excluded": len(excluded),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "meta": meta,
        "targets": [build_target_card(tid) for tid in TARGET_ORDER],
        "eval": {
            "rows": table["rows"],
            "remediation": remediation,
            "notes": notes,
        },
    }


def main():
    data = build()
    validate(data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    size = os.path.getsize(OUT_PATH)

    n_targets = len(data["targets"])
    n_rows = len(data["eval"]["rows"])
    np_targets = sum(1 for c in data["targets"] if c["runs"]["not_proven"] is not None)
    print(
        f"demo_data.json schema v{data['schema_version']}: {n_targets} target card(s) "
        f"(not_proven present on {np_targets}/{n_targets}), {n_rows} eval row(s), "
        f"{data['meta']['receipts_valid']} valid / {data['meta']['receipts_excluded']} "
        f"excluded receipts."
    )
    print(f"  output: {OUT_PATH}  ({size} bytes)")


if __name__ == "__main__":
    main()
