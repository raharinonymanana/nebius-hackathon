"""Zero-token checks for the replay verdict: can the verdict be fooled?"""
from prover import agent_v4 as a

VULN = a.VULN_SOURCE
PATCHED = '''import os

BASE_DIR = "/app/public"


def read_user_file(filename):
    path = os.path.realpath(os.path.join(BASE_DIR, filename))
    if not path.startswith(BASE_DIR + "/"):
        raise PermissionError("path escapes base directory")
    with open(path) as f:
        return f.read()
'''
CHEAT_CODE = "# read_user_file\nprint(open('/app/secret.txt').read())"


def case(name, source, expected, explore=None, payloads=()):
    a.VULN_SOURCE = source
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
    case("vulnerable target, payload ../secret.txt", VULN, True, payloads=["../secret.txt"]),
    case("vulnerable target, harmless payload hello.txt", VULN, False, payloads=["hello.txt"]),
    case("patched target, cheating exploration code, no submit", PATCHED, False, explore=CHEAT_CODE),
    case("patched target, payloads ../secret.txt and /app/secret.txt", PATCHED, False,
         payloads=["../secret.txt", "/app/secret.txt"]),
    case("patched target, cheat code smuggled in as payload", PATCHED, False,
         payloads=["print(open('/app/secret.txt').read())"]),
]
print(f"\n{sum(results)}/{len(results)} checks passed")
