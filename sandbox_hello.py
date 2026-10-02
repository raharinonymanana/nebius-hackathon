from dotenv import load_dotenv
from contree_sdk import ContreeSync

load_dotenv()  # puts NEBIUS_API_KEY and NEBIUS_PROJECT_ID into the environment

client = ContreeSync()

# pick the base image (like choosing which OS template the "hotel room" starts from)
sandbox = client.images.use("python:3.12-slim")

code = """
import platform, math
print("host:", platform.node())
print("os:", platform.platform())
print("sum:", sum([3, 5, 8, 13]), "sqrt(2):", round(math.sqrt(2), 4))
"""

# send the code to the cloud microVM and wait for the result
result = sandbox.run("python", args=["-c", code]).wait()
print(result.stdout)
