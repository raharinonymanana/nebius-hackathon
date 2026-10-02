"""agent_v4: Nemotron tries to PROVE a vulnerability claim inside a Token Factory sandbox.

Exploration runs are NOT evidence. The verdict comes only from a replay: our fixed
harness feeds the model's final payload string to the real target in a fresh branch
of the clean checkpoint. The model controls the input, never the code that runs.
"""
import json
import os
import secrets
import time

from contree_sdk import ContreeSync
from dotenv import load_dotenv
from openai import OpenAI

import costlog

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

VULN_SOURCE = '''import os

BASE_DIR = "/app/public"


def read_user_file(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path) as f:
        return f.read()
'''

# Fixed by us. The only model-controlled part is sys.argv[1], passed as plain data.
HARNESS = '''import sys
sys.path.insert(0, "/app")
import vuln
print(vuln.read_user_file(sys.argv[1]))
'''

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
    return (
        "Target module /app/vuln.py (source below). Claim to test: read_user_file lets "
        "a caller read files OUTSIDE its base directory /app/public (path traversal). "
        "A secret file exists at /app/secret.txt. Explore with run_in_sandbox (Python "
        "code that does sys.path.insert(0, '/app'), imports vuln, calls read_user_file "
        f"and prints the result; at most {MAX_ATTEMPTS} attempts). When you have a "
        "candidate input, call submit_proof once with the exact filename string: the "
        "system replays it through read_user_file and reports whether the secret "
        "leaked. If you have no working input, do not call submit_proof. Then conclude "
        "in at most 3 sentences, based only on tool results.\n\n"
        "--- /app/vuln.py ---\n" + VULN_SOURCE
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
            "Submit the final proof: ONE filename string (max 200 chars). The system "
            "replays it through read_user_file in a fresh sandbox and reports whether "
            "the secret leaked. This is the only thing that confirms a claim."),
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
    setup_code = (
        "import os\n"
        "os.makedirs('/app/public', exist_ok=True)\n"
        "open('/app/public/hello.txt', 'w').write('hello\\n')\n"
        f"open('/app/secret.txt', 'w').write({FLAG!r} + '\\n')\n"
        f"open('/app/vuln.py', 'w').write({VULN_SOURCE!r})\n"
    )
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
            "timeout", args=[str(TIMEOUT_S), "python", "-c", HARNESS, payload],
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
    print(f"\n(run cost ~${run_cost:.5f}; full log: python costlog.py)")


if __name__ == "__main__":
    print("Building clean checkpoint (target + planted canary)...")
    CHECKPOINT = build_checkpoint()
    print(f"Checkpoint image: {getattr(CHECKPOINT, 'uuid', None)}")
    try:
        run_agent()
    finally:
        print_receipts_and_verdict()
