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

CHEAT_CODE = "# read_user_file\nprint(open('/app/static_secret.txt').read())"


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
    case("vulnerable, payload ../static_secret.txt", "vulnerable", True,
         payloads=["../static_secret.txt"]),
    case("vulnerable, harmless payload hello.txt", "vulnerable", False,
         payloads=["hello.txt"]),
    case("fixed, cheating exploration code, no submit", "fixed", False,
         explore=CHEAT_CODE),
    case("fixed, payloads ../static_secret.txt and /app/static_secret.txt", "fixed", False,
         payloads=["../static_secret.txt", "/app/static_secret.txt"]),
    case("fixed, cheat code smuggled in as payload", "fixed", False,
         payloads=["print(open('/app/static_secret.txt').read())"]),
]
print(f"\n{sum(results)}/{len(results)} checks passed")
