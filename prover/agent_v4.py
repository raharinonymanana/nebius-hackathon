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

from prover import costlog

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_STEPS = 8
MAX_TOKENS = 4000
MAX_ATTEMPTS = 3    # exploration runs
MAX_SUBMITS = 2     # replayed proofs
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

SYSTEM = (
    "You are a security research agent. A vulnerability claim counts as confirmed "
    "only if submit_proof reports it. Never invent tool output. "
    "Keep the code you submit short."
)


def make_task():
    mod = SPEC.MODULE_FILENAME[:-3]
    return (
        SPEC.claim() + " "
        "Explore with run_in_sandbox (Python code that does "
        f"sys.path.insert(0, '/app'), imports {mod}, calls {SPEC.ENTRY} and prints "
        f"the result; at most {MAX_ATTEMPTS} attempts). When you have a candidate "
        "input, call submit_proof once with the exact input string: the system "
        "replays it through the target and reports whether the secret leaked. If you "
        "have no working input, do not call submit_proof. Then conclude in at most 3 "
        "sentences, based only on tool results.\n\n"
        f"--- /app/{SPEC.MODULE_FILENAME} ---\n" + SPEC.source(VARIANT)
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
    base = sandbox_client.images.use(BASE_IMAGE)
    res = base.run("python", args=["-c", setup_code], disposable=False).wait()
    if res.exit_code != 0:
        raise SystemExit(f"checkpoint setup failed: {_text(res.stderr)}")
    return res  # a run result is also an image: runs call .run() on it


def run_in_sandbox(code: str) -> dict:
    attempt = len(RECEIPTS) + 1
    if attempt > MAX_ATTEMPTS:
        return {"error": f"attempt limit ({MAX_ATTEMPTS}) reached"}
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


REGISTRY = {"run_in_sandbox": run_in_sandbox, "submit_proof": submit_proof}


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
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": make_task()}]
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
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                print(f"  -> {tc.function.name}")
                result = run_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result)})
            continue

        if not msg.content:
            print("STOP: empty content (check reasoning budget).")
            break
        print("\nMODEL CONCLUSION (not evidence):\n" + msg.content)
        break
    else:
        print("STOP: MAX_STEPS reached without a final answer.")
    print(f"\n(run cost ~${run_cost:.5f}; full log: python -m prover.costlog)")


if __name__ == "__main__":
    print(f"Target: {SPEC.NAME} [{VARIANT}]")
    print("Building clean checkpoint (target + planted canary)...")
    CHECKPOINT = build_checkpoint()
    print(f"Checkpoint image: {getattr(CHECKPOINT, 'uuid', None)}")
    try:
        run_agent()
    finally:
        print_receipts_and_verdict()
        write_receipt()
