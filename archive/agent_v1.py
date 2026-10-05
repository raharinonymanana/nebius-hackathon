import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_STEPS = 6          # guard 1: cap the loop so credits can't burn
MAX_TOKENS = 4000      # generous: hidden reasoning counts against this
PRICE_IN, PRICE_OUT = 0.30, 0.90   # USD per 1M tokens (unverified vs console)

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
)

# --- The tool: a plain Python function. Our code runs it, never the model. ---
CVE_DB = {
    "CVE-2021-44228": {"name": "Log4Shell", "cvss": 10.0, "severity": "Critical"},
    "CVE-2014-0160": {"name": "Heartbleed", "cvss": 7.5, "severity": "High"},
}


def lookup_cve_severity(cve_id: str) -> dict:
    return CVE_DB.get(cve_id.upper(), {"error": f"{cve_id} not found"})


TOOLS = [{
    "type": "function",
    "function": {
        "name": "lookup_cve_severity",
        "description": "Look up name, CVSS score and severity for a CVE id.",
        "parameters": {
            "type": "object",
            "properties": {"cve_id": {"type": "string", "description": "e.g. CVE-2021-44228"}},
            "required": ["cve_id"],
        },
    },
}]
REGISTRY = {"lookup_cve_severity": lookup_cve_severity}


def log_usage(resp, step):
    u = resp.usage
    details = getattr(u, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details else None
    cost = (u.prompt_tokens * PRICE_IN + u.completion_tokens * PRICE_OUT) / 1_000_000
    row = {
        "ts": time.time(), "script": "agent_v1", "model": MODEL, "step": step,
        "in": u.prompt_tokens, "out": u.completion_tokens,
        "reasoning": reasoning, "est_cost_usd": round(cost, 6),
    }
    with open("usage_log.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"  [step {step}] in={u.prompt_tokens} out={u.completion_tokens} "
          f"reasoning={reasoning} ~${cost:.5f}")


def run_agent(question: str):
    messages = [{"role": "user", "content": question}]
    for step in range(1, MAX_STEPS + 1):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=MAX_TOKENS,
        )
        log_usage(resp, step)
        choice = resp.choices[0]
        msg = choice.message

        if choice.finish_reason == "length":  # guard 2: truncated reply
            print("STOP: hit max_tokens (reasoning likely ate the budget).")
            return

        if msg.tool_calls:
            # Echo the assistant's tool request back into the conversation
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [{
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                } for tc in msg.tool_calls],
            })
            # Our code executes each requested tool and returns the result
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                print(f"  -> tool call: {tc.function.name}({args})")
                result = REGISTRY[tc.function.name](**args)
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })
            continue  # call the model again with the tool results

        if not msg.content:  # guard 2: empty reply
            print("STOP: empty content (check reasoning budget).")
            return
        print("\nFINAL ANSWER:\n" + msg.content)
        return

    print("STOP: MAX_STEPS reached without a final answer.")


if __name__ == "__main__":
    run_agent("How severe is Log4Shell? Give the CVE id, CVSS and one-line advice.")
