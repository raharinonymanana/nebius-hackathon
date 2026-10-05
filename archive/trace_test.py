"""One traced Nemotron call through Token Factory, also written to the cost log.
Tracing is switched on here, not in .env, so other scripts stay untraced."""
import os
import time

from dotenv import load_dotenv

load_dotenv()
# Set before importing langsmith so the settings are seen from the start.
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "hackathon-nebius"

from openai import OpenAI  # noqa: E402
from langsmith import traceable  # noqa: E402
from langsmith.wrappers import wrap_openai  # noqa: E402

from costlog import log_call  # noqa: E402

MODEL = "nvidia/nemotron-3-super-120b-a12b"

client = wrap_openai(
    OpenAI(
        base_url="https://api.tokenfactory.nebius.com/v1/",
        api_key=os.environ["NEBIUS_API_KEY"],
    )
)


@traceable(name="trace_test_run")
def run(question: str) -> str:
    start = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        max_tokens=2000,  # generous: reasoning tokens count against this cap
    )
    secs = time.time() - start
    log_call(MODEL, resp, secs, label="trace_test")
    choice = resp.choices[0]
    text = choice.message.content or ""
    usage = resp.usage
    details = getattr(usage, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details else None
    print(
        f"finish_reason={choice.finish_reason} "
        f"input={usage.prompt_tokens} output={usage.completion_tokens} "
        f"reasoning={reasoning}"
    )
    if not text.strip() or choice.finish_reason == "length":
        print("WARNING: empty or truncated reply (reasoning may have used the cap)")
    return text


if __name__ == "__main__":
    print(run("In one sentence, what is a sandbox in computer security?"))
    time.sleep(4)  # let the background sender upload the trace before exit
