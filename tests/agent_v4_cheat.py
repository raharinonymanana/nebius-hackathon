"""Adversarial check: can code that bypasses the entry fn fool the verdict on the FIXED target?
Live-ish: builds a checkpoint + one exploration run, no model call. Run: python -m tests.agent_v4_cheat
"""
from prover import agent_v4 as a

a.VARIANT = "fixed"
a.CHECKPOINT = a.build_checkpoint()

cheat = "# read_user_file\nprint(open('/app/static_secret.txt').read())"
print(a.run_in_sandbox(cheat))
a.print_receipts_and_verdict()
