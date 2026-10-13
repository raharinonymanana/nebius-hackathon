"""Hardened, model-free live-verify service over a ConTree sandbox.

verify(target_key, user_input) proves ONE fixed vulnerability -- the ormar
aggregate SQL injection (CVE-2026-26198) -- by replaying a submitted field name
against the REAL pip-installed ormar inside a disposable ConTree sandbox. There
is no LLM in this path: the verdict is decided solely by whether a planted
canary appears in sandbox stdout. Build for hostile input -- the submitted
string is treated as an attacker's, and the sandbox is assumed to misbehave.

DEPENDENCY BAKING (install leaves the hot path):
v0.3.6 has no Dockerfile/steps builder; the commit mechanism is run(disposable=
False), whose result is a reusable image carrying a committed uuid. So we bake
ormar + aiosqlite (sqlalchemy arrives transitively) ONCE into an image on top of
python:3.12-slim, cache it for the process, and boot every per-request replay
from that image with disposable=True. Baking is one-time infrastructure and is
NOT wrapped by the per-request timeout budget; the hot path never runs pip.

Per request we still: build a FRESH DB, materialise the cartridge + input per
run, decide PROVEN by canary only, and harden the sandbox SQLite connection
(extension loading off, ATTACH/DETACH denied). The submitted string is delivered
as a FILE and read as data -- never interpolated into the shell command, so we
add no shell-injection surface on top of the SQL-injection one.

Verdicts are PROVEN / NOT PROVEN only. A NOT PROVEN is never "safe".
"""
import importlib.util
import os
import threading
import time
from datetime import datetime, timezone

from contree_sdk import ContreeSync
from contree_sdk.auth import IAMAuth
from contree_sdk.config import ContreeConfig

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_SPEC_PATH = os.path.join(_REPO, "targets", "ormar", "spec.py")

# --- policy constants --------------------------------------------------------
WHITELIST = ("ormar",)                 # the ONLY target this service will run
MAX_INPUT_LEN = 2000                   # hard cap on the submitted field name
BASE_IMAGE = "python:3.12-slim"
MODEL_FREE_MARKER = "none (model-free replay)"  # the contract `model` field
_BAKE_TIMEOUT_S = 240.0                # generous; one-time, off the hot path

# --- load the ormar cartridge (reuse its logic/receipt shape; do not reinvent) -
def _load_spec(path):
    spec = importlib.util.spec_from_file_location("ormar_target_spec", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SPEC = _load_spec(_SPEC_PATH)

# SQLite hardening applied INSIDE the sandbox before any cartridge code runs:
# patch sqlite3.connect so every connection (the sync canary bridge AND aiosqlite
# via ormar) loads no extensions and denies ATTACH/DETACH. Defence in depth on
# top of the model-free canary verdict.
_SANDBOX_HARDEN = """\
import sqlite3 as _sq
_orig_connect = _sq.connect
def _hardened_connect(*a, **k):
    c = _orig_connect(*a, **k)
    try:
        c.enable_load_extension(False)
    except Exception:
        pass
    def _auth(action, *rest):
        if action in (_sq.SQLITE_ATTACH, _sq.SQLITE_DETACH):
            return _sq.SQLITE_DENY
        return _sq.SQLITE_OK
    c.set_authorizer(_auth)
    return c
_sq.connect = _hardened_connect
"""

# The in-sandbox runner: harden -> build a FRESH DB (cartridge's own build) ->
# read the hostile input as data from a file -> drive the real cartridge adapter
# and print its result. The canary is bridged file->admin-cell by adapter code.
_SANDBOX_RUNNER = (
    _SANDBOX_HARDEN
    + "\n"
    + SPEC._BUILD_DB
    + "\n"
    + "import sys\n"
    + "sys.path.insert(0, '/app')\n"
    + "with open('/app/user_input.txt', encoding='utf-8') as _f:\n"
    + "    _ui = _f.read()\n"
    + "import vuln\n"
    + "print(vuln.price_stat(_ui))\n"
)

_BAKE_CMD = (
    "python -m pip install --no-cache-dir "
    f"ormar=={SPEC.VULN_VERSION} aiosqlite"
)
_RUN_CMD = "python /app/runner.py"     # NO pip, NO user input in the hot path

# --- process-cached SDK + baked image ----------------------------------------
_SDK = None
_BASE_URL = None
_BAKED = None
_BAKE_LOCK = threading.Lock()


def get_sdk():
    """Build the ConTree SDK once (IAMAuth resolves token/base_url/project_id
    from env / ~/.config, as the spike did) and cache the resolved base_url."""
    global _SDK, _BASE_URL
    if _SDK is None:
        auth = IAMAuth()  # IAMAuth sends the required Project header; JWTAuth does NOT
        _SDK = ContreeSync(config=ContreeConfig(auth=auth))
        _BASE_URL = _SDK.config.auth.base_url  # resolved value, for the Lambda env later
    return _SDK


def resolved_base_url():
    get_sdk()
    return _BASE_URL


def ensure_image():
    """Bake deps ONCE into a reusable image (disposable=False commit) and cache
    it. One-time infrastructure -- deliberately OUTSIDE the per-request budget."""
    global _BAKED
    if _BAKED is None:
        with _BAKE_LOCK:
            if _BAKED is None:
                sdk = get_sdk()
                base = sdk.images.use(BASE_IMAGE)
                _BAKED = base.run(shell=_BAKE_CMD, disposable=False,
                                  timeout=_BAKE_TIMEOUT_S).wait()
    return _BAKED


# --- timeout: the spike's hard client-side daemon-thread budget ---------------
def _run_with_budget(image, cmd, files, budget_s):
    """Run cmd in a disposable sandbox under a HARD client-side wall-clock
    budget. .wait() blocks, so it runs in a daemon thread joined with a
    deadline; a ConTree hang returns control here instead of blocking the
    caller. Returns (result_image | None, elapsed_s, status) where status is
    'ok', 'TIMEOUT', or an exception."""
    box = {}

    def work():
        try:
            box["img"] = image.run(shell=cmd, files=files, disposable=True,
                                   timeout=budget_s).wait()
        except BaseException as e:  # noqa: BLE001 -- surface anything to caller
            box["err"] = e

    t = threading.Thread(target=work, daemon=True)
    t0 = time.monotonic()
    t.start()
    t.join(budget_s)
    dt = time.monotonic() - t0
    if t.is_alive():
        return None, dt, "TIMEOUT"
    if "err" in box:
        return None, dt, box["err"]
    return box["img"], dt, "ok"


# --- receipt builders (contract.ts discriminated union) ----------------------
def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _source_receipt(utc):
    # Synthetic reference for a live run; no file is written (we do not touch
    # receipts/). Follows the engine's <target>_<variant>_<ts>.json convention.
    stamp = utc.replace("-", "").replace(":", "").replace("+00:00", "+0000")
    return f"{SPEC.NAME}_live_{stamp}.json"


def _base_fields(user_input, flag):
    utc = _utc_now()
    return {
        "mode": "handed",
        "input": user_input,
        "canary": flag,
        "model": MODEL_FREE_MARKER,
        "verification_is_model_free": True,
        "utc": utc,
        "source_receipt": _source_receipt(utc),
    }


def _proven(user_input, flag):
    d = _base_fields(user_input, flag)
    d["verdict"] = "PROVEN"
    d["human_trace"] = [
        f"Target whitelist: target_key {WHITELIST[0]!r} accepted "
        "(the function under test is fixed by the cartridge, not the caller).",
        f"Input size check: {len(user_input)} chars <= cap {MAX_INPUT_LEN}.",
        f"ConTree sandbox {BASE_IMAGE} booted from a prebaked image with "
        f"ormar=={SPEC.VULN_VERSION} + aiosqlite; a fresh {SPEC.DB_ABS} was built per request.",
        "SQLite hardened in-sandbox: extension loading disabled, ATTACH/DETACH "
        "denied via authorizer.",
        "Canary FLAG planted into the admin password_hash cell; the submitted "
        "string was delivered as a file and read as data, never interpolated "
        "into the shell command.",
        "Ran the real ormar aggregate replay (Product.objects.max) inside the "
        "sandbox via the sealed cartridge adapter.",
        f"Harness observed the canary {flag} in sandbox stdout with exit 0 (leaked=true).",
        "Verdict: PROVEN - confirmed solely by the model-free ConTree replay harness.",
    ]
    return d


def _not_proven(user_input, flag, note):
    d = _base_fields(user_input, flag)
    d["verdict"] = "NOT PROVEN"
    d["note"] = note  # diagnostic superset field; frontend reads only the union fields
    return d


# --- the single server-side entry point --------------------------------------
def verify(target_key, user_input, *, timeout_s=8.0, base_image=None):
    """Prove the ormar aggregate SQL injection by replaying `user_input` as the
    aggregate field name inside a disposable ConTree sandbox. Model-free;
    canary-only verdict. Returns a dict matching contract.ts (ProvenRun on
    PROVEN, NotProvenRun on NOT PROVEN). Raises ValueError on a rejected input
    (non-whitelisted target_key, or input over MAX_INPUT_LEN).

    base_image: a PRE-BAKED image tag/uuid (deps already installed) to boot the
    replay from -- this is what Lambda passes, so NO install runs on the request
    path. When None (WSL/local), ensure_image() bakes python:3.12-slim once."""
    # 1. WHITELIST -- never run an arbitrary target or arbitrary code.
    if target_key not in WHITELIST:
        raise ValueError(
            f"target_key {target_key!r} is not permitted; "
            f"only {WHITELIST[0]!r} may be verified")
    # 2. SIZE CAP
    if not isinstance(user_input, str):
        raise ValueError("user_input must be a str")
    if len(user_input) > MAX_INPUT_LEN:
        raise ValueError(
            f"user_input length {len(user_input)} exceeds MAX_INPUT_LEN={MAX_INPUT_LEN}")

    # Fresh canary per request (engine's pattern). PROVEN iff THIS shows in stdout.
    flag = "FAKE-" + os.urandom(8).hex()

    # 3. Build the sandbox run. The sandbox gets ONLY the cartridge + input +
    #    canary; no secrets, no process env. All files are bytes (inline
    #    content), so nothing is read from the local host at upload time either.
    files = {
        "/app/vuln.py": SPEC.source("vulnerable").encode("utf-8"),
        "/app/runner.py": _SANDBOX_RUNNER.encode("utf-8"),
        "/app/user_input.txt": user_input.encode("utf-8"),   # hostile string, as DATA
        "/app/secret.txt": (flag + "\n").encode("utf-8"),     # canary flat file
    }

    try:
        sdk = get_sdk()
        if base_image:
            image = sdk.images.use(base_image)  # pre-baked tag/uuid; NO bake on hot path
        else:
            image = ensure_image()              # WSL/local: bake python:3.12-slim once
    except Exception as e:  # noqa: BLE001 -- infra failure is NOT PROVEN, never "safe"
        return _not_proven(user_input, flag,
                           f"sandbox image unavailable: {type(e).__name__}: {e}")

    # 5. TIMEOUT -- hard client-side budget around the replay only.
    result_img, elapsed, status = _run_with_budget(image, _RUN_CMD, files, timeout_s)

    if status == "TIMEOUT":
        return _not_proven(user_input, flag,
                           f"verification timed out after {timeout_s:.1f}s")
    if status != "ok" or result_img is None:
        return _not_proven(user_input, flag,
                           f"sandbox error after {elapsed:.1f}s: {status!r}")

    # 4. CANARY-ONLY verdict: PROVEN iff exit 0 AND the planted canary leaked.
    stdout = result_img.stdout or ""
    leaked = result_img.exit_code == 0 and flag in stdout
    if leaked:
        return _proven(user_input, flag)
    return _not_proven(
        user_input, flag,
        f"canary not leaked (exit={result_img.exit_code}); input did not prove the injection")


# --- self-test (SPENDS ConTree compute; briefed) -----------------------------
if __name__ == "__main__":
    print("resolved base_url:", resolved_base_url())

    t = time.monotonic()
    ensure_image()  # one-time bake, OUTSIDE the per-request budget
    print(f"image bake (one-time, off hot path): {time.monotonic() - t:.2f}s\n")

    def _run(label, target, payload, want):
        try:
            t0 = time.monotonic()
            r = verify(target, payload)
            dt = time.monotonic() - t0
            vd = r["verdict"]
            ok = "OK" if vd == want else "MISMATCH"
            note = f"  note={r.get('note')}" if "note" in r else ""
            print(f"{label}: {vd}  [{ok}, want {want}]  {dt:.2f}s{note}")
            return dt
        except ValueError as e:
            tag = "rejected" if want == "rejected" else "UNEXPECTED-REJECT"
            print(f"{label}: {tag}: {e}  [{'OK' if want == 'rejected' else 'MISMATCH'}]")
            return None

    cold = _run("a) exploit (cold)", "ormar", SPEC.EXPLOIT_INPUT, "PROVEN")
    warm = _run("a) exploit (warm)", "ormar", SPEC.EXPLOIT_INPUT, "PROVEN")
    _run("b) benign          ", "ormar", SPEC.BENIGN_INPUT, "NOT PROVEN")
    _run("c) oversized input ", "ormar", "A" * (MAX_INPUT_LEN + 1), "rejected")
    _run("d) non-whitelist   ", "starlette", SPEC.EXPLOIT_INPUT, "rejected")

    if cold is not None and warm is not None:
        print(f"\ntimings: cold PROVEN {cold:.2f}s | warm PROVEN {warm:.2f}s "
              f"(budget {8.0:.1f}s)")
