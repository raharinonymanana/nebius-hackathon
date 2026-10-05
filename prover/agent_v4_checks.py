"""Live checks for agent_v4 on the FIXED target: timeout receipt + no false positive.
Spends tokens (runs the agent). Run: python -m prover.agent_v4_checks
"""
from prover import agent_v4 as a

a.VARIANT = "fixed"
a.CHECKPOINT = a.build_checkpoint()

print("CHECK 1: infinite loop must hit the timeout (no model call, no token cost)")
print(a.run_in_sandbox("import time\nwhile True:\n    time.sleep(1)"))
a.RECEIPTS.clear()
a.REPLAYS.clear()

print("\nCHECK 2: live agent on the fixed target. Expected verdict: NOT PROVEN")
try:
    a.run_agent()
finally:
    a.print_receipts_and_verdict()
