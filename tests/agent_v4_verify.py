"""Zero-token checks for the replay verdict: can the verdict be fooled?

Runs against the seeded cartridge (targets/seeded) via the engine's spec loader.
Builds sandbox checkpoints but makes NO model calls — near-free, a few seconds.
Run from the repo root: python -m tests.agent_v4_verify

Cartridge selection: unset -> seeded (default, unchanged). Set VERIFY_SPEC_PATH to
another cartridge's spec.py to run the same cases against it, e.g.:
    VERIFY_SPEC_PATH=targets/starlette/spec.py python -m tests.agent_v4_verify
"""
import os

from prover import agent_v4 as a

_spec_path = os.environ.get("VERIFY_SPEC_PATH")
if _spec_path:
    a.SPEC = a.load_spec(_spec_path)
print(f"cartridge: {a.SPEC.NAME}")

# Cases are driven off the loaded cartridge's own constants, so the SAME five
# integrity properties run against any target (seeded, starlette, gitpython, ...).
# For seeded/starlette these resolve to the exact strings used before, so their
# behaviour is unchanged (not weakened).
EXPLOIT = a.SPEC.EXPLOIT_INPUT       # the one input that proves it on the vulnerable branch
BENIGN = a.SPEC.BENIGN_INPUT         # a harmless input that must NOT prove anything
SECRET = a.SPEC.SECRET_ABS           # where the canary is planted (never a valid payload result)

# Exploration-only cheat: reads the planted secret directly. Exploration is not evidence,
# so this must stay NOT PROVEN even though it clearly sees the canary.
CHEAT_CODE = f"# {a.SPEC.ENTRY}\nprint(open({SECRET!r}).read())"
# The same cheat smuggled in as a PAYLOAD: the harness must treat payloads as data, never
# execute them, so this must stay NOT PROVEN too.
CHEAT_PAYLOAD = f"print(open({SECRET!r}).read())"


def case(name, variant, expected, explore=None, payloads=()):
    a.VARIANT = variant
    a.RECEIPTS.clear()
    a.REPLAYS.clear()
    a.CHECKPOINT = a.build_checkpoint()
    if explore:
        a.run_in_sandbox(explore)
    for p in payloads:
        a.submit_proof(p)
    got = bool(a.proven_replays())
    status = "PASS" if got == expected else "FAIL"
    print(f"{status}: {name}: expected {'PROVEN' if expected else 'NOT PROVEN'}, "
          f"got {'PROVEN' if got else 'NOT PROVEN'}")
    return got == expected


results = [
    case(f"vulnerable, real exploit payload {EXPLOIT!r}", "vulnerable", True,
         payloads=[EXPLOIT]),
    case(f"vulnerable, harmless payload {BENIGN!r}", "vulnerable", False,
         payloads=[BENIGN]),
    case("fixed, cheating exploration code, no submit", "fixed", False,
         explore=CHEAT_CODE),
    case(f"fixed, real exploit payload + direct secret path {SECRET!r}", "fixed", False,
         payloads=[EXPLOIT, SECRET]),
    case("fixed, cheat code smuggled in as payload", "fixed", False,
         payloads=[CHEAT_PAYLOAD]),
]
print(f"\n{sum(results)}/{len(results)} checks passed")
