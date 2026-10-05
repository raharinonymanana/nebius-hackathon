from dotenv import load_dotenv
from contree_sdk import ContreeSync

load_dotenv()

client = ContreeSync()
sandbox = client.images.use("python:3.12-slim")


def show(label, result):
    print(f"--- {label} ---")
    for name in dir(result):
        if name.startswith("_"):
            continue
        try:
            value = getattr(result, name)
        except Exception as exc:
            value = f"<error: {exc}>"
        if callable(value):
            continue
        text = repr(value)
        print(f"{name}: {text[:300]}")


show("apt update", sandbox.run("apt-get", args=["update", "-q"]).wait())
show("apt install", sandbox.run("apt-get", args=["install", "-y", "qrencode"]).wait())
show("which qrencode", sandbox.run("which", args=["qrencode"]).wait())
