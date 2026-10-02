import time
from dotenv import load_dotenv
from contree_sdk import ContreeSync

load_dotenv()

client = ContreeSync()
sandbox = client.images.use("python:3.12-slim")

t0 = time.perf_counter()
sandbox.run("apt-get", args=["update", "-q"]).wait()
sandbox.run("apt-get", args=["install", "-y", "qrencode"]).wait()
t1 = time.perf_counter()
print(f"apt install took {t1 - t0:.1f}s")

# code a model might generate: it needs the tool installed in the previous step
generated_code = """
import subprocess
qr = subprocess.run(
    ["qrencode", "-t", "ANSIUTF8", "https://tokenfactory.nebius.com"],
    capture_output=True, text=True,
)
print(qr.stdout)
"""

result = sandbox.run("python", args=["-c", generated_code]).wait()
print(result.stdout)
print(f"code run took {time.perf_counter() - t1:.1f}s")
