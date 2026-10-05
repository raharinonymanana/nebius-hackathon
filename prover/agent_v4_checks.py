"""Live checks for agent_v4 on a PATCHED target: timeout receipt + no false positive."""
from prover import agent_v4 as a

PATCHED = '''import os

BASE_DIR = "/app/public"


def read_user_file(filename):
    path = os.path.realpath(os.path.join(BASE_DIR, filename))
    if not path.startswith(BASE_DIR + "/"):
        raise PermissionError("path escapes base directory")
    with open(path) as f:
        return f.read()
'''

a.VULN_SOURCE = PATCHED
a.CHECKPOINT = a.build_checkpoint()

print("CHECK 1: infinite loop must hit the timeout (no model call, no token cost)")
print(a.run_in_sandbox("import time\nwhile True:\n    time.sleep(1)"))
a.RECEIPTS.clear()
a.REPLAYS.clear()

print("\nCHECK 2: live agent on the patched target. Expected verdict: NOT PROVEN")
try:
    a.run_agent()
finally:
    a.print_receipts_and_verdict()
