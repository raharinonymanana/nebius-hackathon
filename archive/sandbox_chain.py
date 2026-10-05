from dotenv import load_dotenv
from contree_sdk import ContreeSync

load_dotenv()

client = ContreeSync()
base = client.images.use("python:3.12-slim")

# checkpoint 1: tool installed, state saved (disposable=False)
tooled = base.run(
    shell="apt-get update -q >/dev/null && apt-get install -y qrencode >/dev/null",
    disposable=False,
).wait()
print("checkpoint 1 uuid:", tooled.uuid, "| exit:", tooled.exit_code)

# a separate run from that checkpoint should now find the tool
seen = tooled.run(shell="which qrencode").wait()
print("separate run sees qrencode:", seen.stdout.strip(), "| exit:", seen.exit_code)

# two branches from the SAME checkpoint
branch_a = tooled.run(shell="echo A > /tmp/note.txt", disposable=False).wait()
branch_b = tooled.run(shell="echo B > /tmp/note.txt", disposable=False).wait()
print("branch A uuid:", branch_a.uuid)
print("branch B uuid:", branch_b.uuid)

# each branch sees only its own note, and both still have the tool
for name, branch in (("A", branch_a), ("B", branch_b)):
    r = branch.run(shell="cat /tmp/note.txt; which qrencode").wait()
    print(f"branch {name} ->", r.stdout.strip().replace("\n", " | "))

# the parent checkpoint must be untouched (no note file)
parent = tooled.run(shell="ls /tmp/note.txt").wait()
print("parent has note.txt? exit:", parent.exit_code, "(non-zero means untouched)")
