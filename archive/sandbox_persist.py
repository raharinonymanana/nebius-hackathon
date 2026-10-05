from dotenv import load_dotenv
from contree_sdk import ContreeSync

load_dotenv()

client = ContreeSync()
sandbox = client.images.use("python:3.12-slim")

# call 1: update + install + check, all inside ONE run
r1 = sandbox.run(
    "sh",
    args=["-c", "apt-get update -q >/dev/null && apt-get install -y qrencode >/dev/null && which qrencode"],
).wait()
print("call 1 exit:", r1.exit_code, "| stdout:", r1.stdout.strip(), "| stderr:", r1.stderr.strip()[:200])

# call 2: a separate run on the same sandbox object
r2 = sandbox.run("which", args=["qrencode"]).wait()
print("call 2 exit:", r2.exit_code, "| stdout:", r2.stdout.strip())
