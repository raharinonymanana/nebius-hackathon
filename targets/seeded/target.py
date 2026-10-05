"""
Seeded mini-target for the prover — Phase 1.

A tiny read_file() that reproduces the SAME bug class as Starlette's
StaticFiles path traversal (CVE-2023-29159): a weak containment check using
os.path.commonprefix (plain string prefix) instead of os.path.commonpath
(whole path components). The `fixed` flag flips vulnerable <-> patched.

No external deps. No network. No model/API calls (nothing to cost-log).
The replay harness (next step) plants a RANDOM canary as the "secret" and
replays the model's single input string through read_file() to decide
PROVEN / NOT PROVEN. This file's __main__ block is only a build-time
confirm that the seeded bug reproduces — it is NOT the agent verdict.
"""

import os


def read_file(static_dir: str, name: str, *, fixed: bool = False) -> str:
    """Serve `name` from under `static_dir`. Meant to allow ONLY files
    inside static_dir. The vulnerable check lets a sibling whose path
    string-starts-with static_dir slip through."""
    base = os.path.realpath(static_dir)
    full = os.path.realpath(os.path.join(base, name))

    if fixed:
        # PATCHED: component-wise. ".../static_secret.txt" vs ".../static"
        # share the PARENT, not ".../static" -> sibling rejected.
        if os.path.commonpath([full, base]) != base:
            raise PermissionError(f"outside static dir: {name}")
    else:
        # VULNERABLE: string prefix. ".../static_secret.txt".startswith(
        # ".../static") is True -> check passes, file leaks.
        if os.path.commonprefix([full, base]) != base:
            raise PermissionError(f"outside static dir: {name}")

    with open(full, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    # Build-time confirm (fixed canary here; the harness uses a random one).
    import tempfile

    root = tempfile.mkdtemp(prefix="seeded_")
    static_dir = os.path.join(root, "static")
    os.makedirs(static_dir)

    with open(os.path.join(static_dir, "hello.txt"), "w") as f:
        f.write("public hello\n")

    canary = "FAKE-deadbeef"  # the "secret", a SIBLING of static_dir
    with open(os.path.join(root, "static_secret.txt"), "w") as f:
        f.write(canary + "\n")

    attack = "../static_secret.txt"  # one short input string

    # benign read must work on both variants
    assert read_file(static_dir, "hello.txt").strip() == "public hello"
    assert read_file(static_dir, "hello.txt", fixed=True).strip() == "public hello"

    # VULN leaks the canary; FIXED blocks the same input
    vuln_ok = (read_file(static_dir, attack).strip() == canary)
    try:
        read_file(static_dir, attack, fixed=True)
        fixed_ok = False
    except PermissionError:
        fixed_ok = True

    print(f"static_dir   : {static_dir}")
    print(f"attack input : {attack!r}")
    print(f"VULN  leaks canary ? {'YES (bug reproduced)' if vuln_ok else 'no'}")
    print(f"FIXED blocks attack? {'YES (patched)' if fixed_ok else 'no'}")
    print("RESULT:", "PASS — seeded target is faithful" if (vuln_ok and fixed_ok) else "FAIL")
