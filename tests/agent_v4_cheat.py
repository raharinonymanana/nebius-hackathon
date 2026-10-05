"""Adversarial check: can code that bypasses read_user_file fool the verdict on a PATCHED target?"""
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

cheat = "# read_user_file\nprint(open('/app/secret.txt').read())"
print(a.run_in_sandbox(cheat))
a.print_receipts_and_verdict()
