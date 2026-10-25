"""Target spec: seeded mini-target (the first, hand-built cartridge).

A 'cartridge' the prover engine loads instead of a hardcoded target. It declares
the two source branches, where the target lives in the sandbox, where the canary
secret is planted, and the claim the agent tests. Every real target
(targets/starlette, gitpython, ormar) is another folder
with its own spec.py — the engine does not change.

Faithful to Starlette StaticFiles path traversal (CVE-2023-29159): the canary is a
SIBLING of the base dir whose name shares 'static' as a string prefix, so it fools
commonprefix (vulnerable) but not commonpath (fixed).
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

NAME = "seeded-static-traversal"
MODULE_FILENAME = "vuln.py"             # written into the sandbox at /app/vuln.py
ENTRY = "read_user_file"                # harness calls vuln.read_user_file(input_string)
BASE_DIR = "/app/static"                # the dir the target is meant to serve from
SECRET_ABS = "/app/static_secret.txt"   # canary planted here (sibling, shares 'static')
BENIGN_FILES = {"/app/static/hello.txt": "public hello\n"}  # so benign reads work

EXPLOIT_INPUT = "../static_secret.txt"  # the one string that proves it (tests only)
BENIGN_INPUT = "hello.txt"              # a safe read that must work on both branches


def source(variant="vulnerable"):
    """Return the target source text for the chosen branch ('vulnerable'/'fixed')."""
    fname = "vulnerable.py" if variant == "vulnerable" else "fixed.py"
    with open(os.path.join(_HERE, fname), encoding="utf-8") as f:
        return f.read()


def claim():
    return (
        f"Target module /app/{MODULE_FILENAME} serves files from {BASE_DIR}. "
        f"Claim to test: {ENTRY} lets a caller read files OUTSIDE {BASE_DIR} "
        "(path traversal). A secret file exists as a sibling of that directory."
    )


def harness_code():
    """The FIXED replay harness. The model controls only sys.argv[1] (plain data)."""
    mod = MODULE_FILENAME[:-3]
    return (
        "import sys\n"
        "sys.path.insert(0, '/app')\n"
        f"import {mod}\n"
        f"print({mod}.{ENTRY}(sys.argv[1]))\n"
    )


if __name__ == "__main__":
    # Faithful build-time confirm (temp dir stands in for /app/static; random-free canary).
    import importlib.util
    import tempfile

    def _load(variant, base):
        s = importlib.util.spec_from_file_location(
            f"seeded_{variant}", os.path.join(_HERE, f"{variant}.py"))
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        m.BASE_DIR = base  # point the hardcoded /app/static at our temp dir
        return m

    root = tempfile.mkdtemp(prefix="seeded_")
    static = os.path.join(root, "static")
    os.makedirs(static)
    open(os.path.join(static, "hello.txt"), "w").write("public hello\n")
    canary = "FAKE-deadbeef"
    open(os.path.join(root, "static_secret.txt"), "w").write(canary + "\n")

    attack = EXPLOIT_INPUT
    vuln = _load("vulnerable", static)
    fixed = _load("fixed", static)

    ok_benign = (vuln.read_user_file(BENIGN_INPUT).strip() == "public hello"
                 and fixed.read_user_file(BENIGN_INPUT).strip() == "public hello")
    vuln_leaks = (vuln.read_user_file(attack).strip() == canary)
    try:
        fixed.read_user_file(attack)
        fixed_blocks = False
    except PermissionError:
        fixed_blocks = True

    print(f"benign read OK on both ? {'YES' if ok_benign else 'no'}")
    print(f"VULN  leaks canary     ? {'YES' if vuln_leaks else 'no'}")
    print(f"FIXED blocks attack    ? {'YES' if fixed_blocks else 'no'}")
    print("RESULT:", "PASS — faithful commonprefix/commonpath pair"
          if (ok_benign and vuln_leaks and fixed_blocks) else "FAIL")
