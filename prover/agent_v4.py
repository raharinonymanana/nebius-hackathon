"""agent_v4: Nemotron tries to PROVE a vulnerability claim inside a Token Factory sandbox.

Exploration runs are NOT evidence. The verdict comes only from a replay: our fixed
harness feeds the model's final payload string to the real target in a fresh branch
of the clean checkpoint. The model controls the input, never the code that runs.

The target is a swappable "cartridge": a folder with vulnerable.py / fixed.py / spec.py.
The engine loads one spec by file path (default: targets/seeded) and never hardcodes a
target. Phase 2's Starlette target is another folder with its own spec.py; no engine edit.
"""
import importlib.util
import json
import os
import secrets
import time

from contree_sdk import ContreeSync
from dotenv import load_dotenv
from openai import OpenAI

from prover import advisory, costlog

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_STEPS = 8
MAX_TOKENS = 4000
MAX_ATTEMPTS = 4    # exploration runs
MAX_SUBMITS = 3     # replayed proofs
MAX_ADVISORY_CALLS = 2  # model-initiated search_advisory calls per run (our cap, enforced)
PAYLOAD_MAX = 200
TIMEOUT_S = 20
BASE_IMAGE = "python:3.12-slim"

FLAG = "FAKE-" + secrets.token_hex(8)  # canary planted by us, unknown to the model

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SPEC_PATH = os.path.join(_REPO_ROOT, "targets", "seeded", "spec.py")


def load_spec(path):
    """Load a target cartridge's spec.py from a file path (no package needed)."""
    ms = importlib.util.spec_from_file_location("target_spec", path)
    mod = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(mod)
    return mod


SPEC = load_spec(DEFAULT_SPEC_PATH)  # swappable: tests may set a.SPEC
VARIANT = "vulnerable"               # swappable: 'vulnerable' or 'fixed'

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
)
sandbox_client = ContreeSync()

CHECKPOINT = None   # clean image with the target installed; every run branches from it
RECEIPTS = []       # exploration runs (NOT evidence)
REPLAYS = []        # replayed proofs (the only evidence), written by OUR code
ADVISORY = None     # CONTEXT ONLY: mandatory Tavily advisory block; never a verdict input
advisory_tool_calls = []  # CONTEXT ONLY: model-initiated search_advisory results (auditable)

# A2 locate mode (orchestration + measurement only; never a verdict input).
TASK_MODE = "handed"            # requested mode: "handed" (default) or "locate"
TASK_MODE_EFFECTIVE = "handed"  # after fallback (locate needs CVE + TARGET_FUNCTION)
TARGET_FUNCTION = getattr(SPEC, "TARGET_FUNCTION", None)
located_context_supplied = []   # strings WE put into the model's context this run
located_model_said = []         # the model's own content + tool-call args this run

SYSTEM = (
    "You are a security research agent. A vulnerability claim counts as confirmed "
    "only if submit_proof reports it. Never invent tool output. "
    "Keep the code you submit short."
)


def _advisory_context_block():
    """A short, read-only advisory block for the prompt, built ONLY from cited_sources.
    Returns '' when there is no usable advisory (so the run proceeds exactly as before).
    CONTEXT ONLY — it carries no proof and never affects the verdict."""
    adv = ADVISORY
    if not adv or adv.get("error") or not adv.get("cited_sources"):
        return ""
    lines = ["ADVISORY CONTEXT (reference only; it does NOT prove anything — you must "
             "still find and trigger the flaw yourself):"]
    for s in adv["cited_sources"][:3]:
        lines.append(f"- {s.get('title') or '(no title)'} <{s.get('url')}>")
    lines.append(f"(fixed version {adv.get('fixed_version')} mentioned in sources: "
                 f"{adv.get('advisory_consistent')})")
    return "\n".join(lines) + "\n\n"


def _make_locate_task(advisory_hint):
    """'locate' mode: no adapter source, no 'function X is vulnerable' claim. The model
    must DISCOVER the vulnerable function itself by exploring the sandbox, then trigger it.
    Advisory text remains CONTEXT ONLY."""
    prompt = (
        SPEC.claim() + " "
        "You are NOT given the target's source. LOCATE the specific function that "
        "implements the flaw yourself: use run_in_sandbox (arbitrary Python 3) to explore "
        "the sandbox — walk and grep the installed package and /app, and read the code you "
        "find — and identify the exact function where the traversal happens. Do recon "
        "BEFORE guessing an input. "
        + advisory_hint +
        "Then craft an input and call submit_proof once with the exact input string: the "
        "system replays it through the target and reports whether the secret leaked. "
        "Exploration output is not evidence; submit_proof is the only thing that proves the "
        "claim. If you have no working input, do not call submit_proof. Then conclude in at "
        "most 3 sentences, naming the function you located, based only on tool results. "
        f"You have a tool search_advisory. The published security advisory for this CVE "
        f"({getattr(SPEC, 'CVE', None)}) usually names the vulnerable function and file — "
        "consulting it is good practice and often the fastest way to locate the sink. "
        "Using it is optional; your proof is judged only by replay, never by which tools "
        "you used.\n\n"
        + _advisory_context_block()
    )
    # Measurement-integrity guard: the locate prompt must NEVER name the target function,
    # or located_unaided would be dishonest. (The advisory block carries titles/URLs only.)
    tf = getattr(SPEC, "TARGET_FUNCTION", None)
    if tf and tf.lower() in prompt.lower():
        raise SystemExit(
            f"locate prompt leaks TARGET_FUNCTION {tf!r}; refusing to run (would make "
            "located_unaided dishonest)")
    return prompt


def make_task():
    mod = SPEC.MODULE_FILENAME[:-3]
    cve = getattr(SPEC, "CVE", None)
    advisory_hint = (
        f"This target tracks {cve}. A search_advisory(cve) tool is available: it returns "
        "the official advisory from authoritative sources only, and consulting it before "
        "you guess is good practice — but it is REFERENCE ONLY and proves nothing; you must "
        "still find and trigger the flaw yourself and submit a working input. "
    ) if cve else ""
    if TASK_MODE_EFFECTIVE == "locate" and cve and getattr(SPEC, "TARGET_FUNCTION", None):
        return _make_locate_task(advisory_hint)
    return (
        SPEC.claim() + " "
        "Explore with run_in_sandbox (arbitrary Python 3 in the sandbox; "
        f"use sys.path.insert(0, '/app') and import {mod} when you want to call "
        f"{SPEC.ENTRY}). Do recon BEFORE guessing an input: inspect the filesystem "
        "to learn what is actually there — e.g. list the served directory and its "
        "parent (os.listdir), walk nearby directories, and read any files you find "
        "to discover their real names and contents — then craft a payload from what "
        f"you observed rather than a guessed name (at most {MAX_ATTEMPTS} attempts). "
        + advisory_hint +
        "When you have a candidate input, call submit_proof once with the exact input "
        "string: the system replays it through the target and reports whether the "
        "secret leaked. Exploration output is not evidence; submit_proof is the only "
        "thing that proves the claim. If you have no working input, do not call "
        "submit_proof. Then conclude in at most 3 sentences, based only on tool "
        "results.\n\n"
        + _advisory_context_block()
        + f"--- /app/{SPEC.MODULE_FILENAME} ---\n" + SPEC.source(VARIANT)
    )


TOOLS = [
    {"type": "function", "function": {
        "name": "run_in_sandbox",
        "description": (
            "Exploration only. Run Python 3 code in an isolated sandbox that contains "
            f"the target in /app. Every call starts from the same clean state. Timeout "
            f"{TIMEOUT_S} s. Returns exit_code, stdout, stderr, seconds, timed_out."),
        "parameters": {"type": "object",
                       "properties": {"code": {"type": "string"}},
                       "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "submit_proof",
        "description": (
            "Submit the final proof: ONE input string (max 200 chars). The system "
            "replays it through the target in a fresh sandbox and reports whether the "
            "secret leaked. This is the only thing that confirms a claim."),
        "parameters": {"type": "object",
                       "properties": {"payload": {"type": "string"}},
                       "required": ["payload"]}}},
    {"type": "function", "function": {
        "name": "search_advisory",
        "description": (
            "Look up the official security advisory for a CVE from authoritative sources "
            "(GitHub Advisory DB, NVD, OSV, CVE.org). Returns cited titles+URLs and whether "
            "the stated fixed version is consistent. This is REFERENCE ONLY — it does not "
            "prove anything; you must still find and trigger the flaw yourself."),
        "parameters": {"type": "object",
                       "properties": {"cve": {"type": "string"},
                                      "extra_terms": {"type": "string"}},
                       "required": ["cve"]}}},
]


def _text(x):
    if x is None:
        return ""
    if isinstance(x, bytes):
        return x.decode("utf-8", "replace")
    return x if isinstance(x, str) else str(x)


def build_checkpoint():
    lines = ["import os", "os.makedirs('/app', exist_ok=True)"]
    for path, content in SPEC.BENIGN_FILES.items():
        lines.append(f"os.makedirs({os.path.dirname(path)!r}, exist_ok=True)")
        lines.append(f"open({path!r}, 'w').write({content!r})")
    lines.append(f"open({SPEC.SECRET_ABS!r}, 'w').write({FLAG!r} + '\\n')")
    lines.append(
        f"open('/app/{SPEC.MODULE_FILENAME}', 'w').write({SPEC.source(VARIANT)!r})")
    setup_code = "\n".join(lines) + "\n"
    image = sandbox_client.images.use(BASE_IMAGE)
    # Optional, generic dep hook: run any deps the spec declares BEFORE writing files.
    # A ContreeSync run result is itself an image, so chain each step onto the last.
    # Seeded targets have no setup_commands(), so the default is empty and they are untouched.
    for command, cmd_args in getattr(SPEC, "setup_commands", lambda _v: [])(VARIANT):
        image = image.run(command, args=cmd_args, disposable=False).wait()
        if image.exit_code != 0:
            raise SystemExit(f"checkpoint dep step failed: {_text(image.stderr)}")
    res = image.run("python", args=["-c", setup_code], disposable=False).wait()
    if res.exit_code != 0:
        raise SystemExit(f"checkpoint setup failed: {_text(res.stderr)}")
    return res  # a run result is also an image: runs call .run() on it


def run_in_sandbox(code: str) -> dict:
    attempt = len(RECEIPTS) + 1
    if attempt > MAX_ATTEMPTS:
        return {"error": (
            f"Exploration budget exhausted ({MAX_ATTEMPTS}/{MAX_ATTEMPTS} attempts "
            "used). Do NOT call run_in_sandbox again — it will keep failing. Next: "
            "submit your best payload with submit_proof, or call search_advisory to "
            "look up the advisory that names the vulnerable function.")}
    t0 = time.perf_counter()
    try:
        res = CHECKPOINT.run(
            "timeout", args=[str(TIMEOUT_S), "python", "-c", code], disposable=False
        ).wait()
    except Exception as exc:  # noqa: BLE001
        RECEIPTS.append({"attempt": attempt, "image": None, "exit_code": None,
                         "secs": round(time.perf_counter() - t0, 2), "timed_out": False,
                         "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"})
        return {"error": f"{type(exc).__name__}: {exc}"}
    secs = round(time.perf_counter() - t0, 2)
    out, err = _text(res.stdout), _text(res.stderr)
    RECEIPTS.append({"attempt": attempt, "image": getattr(res, "uuid", None),
                     "exit_code": res.exit_code, "secs": secs,
                     "timed_out": res.exit_code == 124, "stdout": out, "stderr": err})
    return {"exit_code": res.exit_code, "stdout": out[:2000], "stderr": err[:1000],
            "seconds": secs, "timed_out": res.exit_code == 124}


def submit_proof(payload: str) -> dict:
    n = len(REPLAYS) + 1
    if n > MAX_SUBMITS:
        return {"error": f"submit limit ({MAX_SUBMITS}) reached"}
    if not isinstance(payload, str) or not payload or len(payload) > PAYLOAD_MAX:
        return {"error": f"payload must be a non-empty string of at most {PAYLOAD_MAX} characters"}
    t0 = time.perf_counter()
    try:
        res = CHECKPOINT.run(
            "timeout",
            args=[str(TIMEOUT_S), "python", "-c", SPEC.harness_code(), payload],
            disposable=False,
        ).wait()
    except Exception as exc:  # noqa: BLE001
        REPLAYS.append({"submit": n, "payload": payload, "image": None, "exit_code": None,
                        "secs": round(time.perf_counter() - t0, 2), "leaked": False,
                        "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"})
        return {"error": f"{type(exc).__name__}: {exc}"}
    secs = round(time.perf_counter() - t0, 2)
    out, err = _text(res.stdout), _text(res.stderr)
    leaked = res.exit_code == 0 and FLAG in out
    REPLAYS.append({"submit": n, "payload": payload, "image": getattr(res, "uuid", None),
                    "exit_code": res.exit_code, "secs": secs, "leaked": leaked,
                    "stdout": out, "stderr": err})
    return {"leaked_secret": leaked, "exit_code": res.exit_code,
            "stderr": err[:300], "seconds": secs}


def proven_replays():
    return [r for r in REPLAYS if r["leaked"]]


def _decide_located_unaided(target_function, supplied_strings, model_strings,
                            mode_effective):
    """Pure measurement (context-only, never a verdict input). 'located_unaided' is true
    only when the model referenced the target function AND we never supplied its name."""
    if not target_function:
        return {"target_function": target_function, "advisory_named_function": None,
                "model_identified_function": None, "located_unaided": False}
    tfl = target_function.lower()
    advisory_named = any(tfl in (s or "").lower() for s in supplied_strings)
    model_identified = any(tfl in (s or "").lower() for s in model_strings)
    return {
        "target_function": target_function,
        "advisory_named_function": advisory_named,
        "model_identified_function": model_identified,
        "located_unaided": (mode_effective == "locate" and model_identified
                            and not advisory_named),
    }


def _locate_measurement():
    return _decide_located_unaided(TARGET_FUNCTION, located_context_supplied,
                                   located_model_said, TASK_MODE_EFFECTIVE)


def _compact_advisory(adv):
    """Model-facing view: cve, consistency, top-3 cited (title/url/origin), note.
    NEVER exposes discarded_sources or raw page content."""
    return {
        "cve": adv.get("cve"),
        "advisory_consistent": adv.get("advisory_consistent"),
        "cited_sources": [{"title": s.get("title"), "url": s.get("url"),
                           "origin": s.get("origin")}
                          for s in (adv.get("cited_sources") or [])[:3]],
        "note": adv.get("note"),
    }


def search_advisory(cve: str, extra_terms: str = "") -> dict:
    """Optional recon tool (CONTEXT ONLY). Capped at MAX_ADVISORY_CALLS actual lookups
    per run; reuses advisory.lookup_advisory (no second search path, no double-logging)."""
    used = len(advisory_tool_calls)
    if used >= MAX_ADVISORY_CALLS:
        return {"error": "advisory lookup limit reached", "calls_used": used,
                "limit": MAX_ADVISORY_CALLS}
    adv = advisory.lookup_advisory(
        cve, getattr(SPEC, "FIXED_VERSION", None), extra_terms=extra_terms or "")
    advisory_tool_calls.append(adv)  # full dict kept for the receipt (auditable)
    return _compact_advisory(adv)


REGISTRY = {"run_in_sandbox": run_in_sandbox, "submit_proof": submit_proof,
            "search_advisory": search_advisory}


def run_tool(name, raw_args):
    try:
        args = json.loads(raw_args)
        if name not in REGISTRY:
            return {"error": f"unknown tool {name}"}
        return REGISTRY[name](**args)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def print_receipts_and_verdict():
    print("\nEXPLORATION RUNS (not evidence):")
    if not RECEIPTS:
        print("  none")
    for r in RECEIPTS:
        print(f"  attempt {r['attempt']}: exit={r['exit_code']} secs={r['secs']} "
              f"timed_out={r['timed_out']} canary_seen={FLAG in r['stdout']} image={r['image']}")
    print("\nREPLAYS (the only evidence: fixed harness, model supplies the input string only):")
    if not REPLAYS:
        print("  none: no proof was submitted")
    for r in REPLAYS:
        print(f"  submit {r['submit']}: payload={r['payload']!r} exit={r['exit_code']} "
              f"secs={r['secs']} leaked_secret={r['leaked']} image={r['image']}")
    proven = proven_replays()
    if proven:
        print(f"\nVERDICT (decided by code): PROVEN by replay {proven[0]['submit']} "
              f"with payload {proven[0]['payload']!r}")
    else:
        print("\nVERDICT (decided by code): NOT PROVEN")


def write_receipt():
    """Dump the run to receipts/<target>_<variant>_<UTC>.json. Audit trail, NOT evidence:
    the live verdict is decided by proven_replays(); this only records what happened."""
    import datetime
    proven = proven_replays()
    record = {
        "target": SPEC.NAME,
        "variant": VARIANT,
        "model": MODEL,
        "canary": FLAG,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "exploration_runs_not_evidence": RECEIPTS,
        "replays_only_evidence": REPLAYS,
        "verdict": "PROVEN" if proven else "NOT PROVEN",
        "proven_by": (proven[0]["submit"] if proven else None),
        "advisory": ADVISORY,  # CONTEXT ONLY; auditable, never a verdict input
        "advisory_tool_calls": advisory_tool_calls,  # model-initiated lookups (may be [])
        "task_mode": TASK_MODE,                  # requested mode
        "task_mode_effective": TASK_MODE_EFFECTIVE,  # after fallback
        "budget": {"MAX_STEPS": MAX_STEPS, "MAX_ATTEMPTS": MAX_ATTEMPTS,
                   "MAX_SUBMITS": MAX_SUBMITS},   # active budget for this run (auditable)
        "locate": _locate_measurement(),         # measurement only; never a verdict input
    }
    out_dir = os.path.join(_REPO_ROOT, "receipts")
    os.makedirs(out_dir, exist_ok=True)
    stamp = record["utc"].replace(":", "").replace("-", "").replace(".", "")
    path = os.path.join(out_dir, f"{SPEC.NAME}_{VARIANT}_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)
    print(f"\nReceipt written: {os.path.relpath(path, _REPO_ROOT)}")
    return path


def run_agent():
    task = make_task()
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    # Measurement capture (context-only): strings WE supplied to the model's context.
    located_context_supplied.extend([SYSTEM, task])
    run_cost = 0.0
    for step in range(1, MAX_STEPS + 1):
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=MAX_TOKENS,
        )
        secs = time.perf_counter() - t0
        costlog.log_call(MODEL, resp, secs, label=f"agent_v4 step {step}")
        u = resp.usage
        cost = costlog.cost_usd(MODEL, u.prompt_tokens, u.completion_tokens) or 0.0
        run_cost += cost
        print(f"  [step {step}] in={u.prompt_tokens} out={u.completion_tokens} "
              f"{secs:.1f}s ~${cost:.5f}")
        choice = resp.choices[0]
        msg = choice.message

        if choice.finish_reason == "length":
            print("STOP: hit max_tokens (reasoning likely ate the budget).")
            break

        if msg.tool_calls:
            if msg.content:
                located_model_said.append(msg.content)  # model's own words
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                located_model_said.append(tc.function.arguments or "")  # model-written args
                print(f"  -> {tc.function.name}")
                result = run_tool(tc.function.name, tc.function.arguments)
                if tc.function.name == "search_advisory":
                    # a search_advisory result is context WE supplied back to the model
                    located_context_supplied.append(json.dumps(result))
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result)})
            continue

        if not msg.content:
            print("STOP: empty content (check reasoning budget).")
            break
        located_model_said.append(msg.content)  # model's final conclusion
        print("\nMODEL CONCLUSION (not evidence):\n" + msg.content)
        break
    else:
        print("STOP: MAX_STEPS reached without a final answer.")
    print(f"\n(run cost ~${run_cost:.5f}; full log: python -m prover.costlog)")


if __name__ == "__main__":
    # Live-run cartridge/branch selection via env (defaults unchanged when unset).
    _spec_path = os.environ.get("TARGET_SPEC_PATH")
    if _spec_path:
        SPEC = load_spec(_spec_path)
    _variant = os.environ.get("TARGET_VARIANT")
    if _variant:
        VARIANT = _variant
    # Run-mode selection. 'locate' needs a known CVE + TARGET_FUNCTION; else fall back.
    TASK_MODE = os.environ.get("TASK_MODE", "handed")
    TARGET_FUNCTION = getattr(SPEC, "TARGET_FUNCTION", None)
    if (TASK_MODE == "locate" and getattr(SPEC, "CVE", None) and TARGET_FUNCTION):
        TASK_MODE_EFFECTIVE = "locate"
    else:
        TASK_MODE_EFFECTIVE = "handed"
    if TASK_MODE == "locate" and TASK_MODE_EFFECTIVE == "handed":
        print("TASK_MODE=locate requested but CVE/TARGET_FUNCTION missing -> handed.")
    # Lever 3: per-mode budget. Handed keeps the defaults (8/4/3); locate gets more room.
    if TASK_MODE_EFFECTIVE == "locate":
        MAX_STEPS, MAX_ATTEMPTS, MAX_SUBMITS = 12, 6, 3
    print(f"Target: {SPEC.NAME} [{VARIANT}]  mode={TASK_MODE_EFFECTIVE} "
          f"(requested {TASK_MODE})")
    print(f"Budget: mode={TASK_MODE_EFFECTIVE} MAX_STEPS={MAX_STEPS} "
          f"MAX_ATTEMPTS={MAX_ATTEMPTS} MAX_SUBMITS={MAX_SUBMITS}")

    advisory_tool_calls.clear()      # run-state init for the optional model-callable tool
    located_context_supplied.clear()  # run-state init for the locate measurement
    located_model_said.clear()

    # Mandatory advisory lookup (CONTEXT ONLY; never a verdict input). Once per run.
    _cve = getattr(SPEC, "CVE", None)
    _fixed = getattr(SPEC, "FIXED_VERSION", None)
    if _cve:
        print(f"Advisory lookup (Tavily, context only) for {_cve}...")
        ADVISORY = advisory.lookup_advisory(
            _cve, _fixed, extra_terms=SPEC.NAME.replace("-", " "))
        if ADVISORY.get("error"):
            print(f"  advisory lookup degraded: {ADVISORY['error']} (run continues)")
        else:
            print(f"  cited={len(ADVISORY['cited_sources'])} "
                  f"credits={ADVISORY.get('credits')} req={ADVISORY.get('request_id')}")
    else:
        ADVISORY = None
        print("No SPEC.CVE — skipping advisory lookup.")

    print("Building clean checkpoint (target + planted canary)...")
    CHECKPOINT = build_checkpoint()
    print(f"Checkpoint image: {getattr(CHECKPOINT, 'uuid', None)}")
    try:
        run_agent()
    finally:
        print_receipts_and_verdict()
        write_receipt()
