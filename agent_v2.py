import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv()

MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_STEPS = 8
MAX_TOKENS = 4000
PRICE_IN, PRICE_OUT = 0.30, 0.90   # USD per 1M tokens (unverified vs console)

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ["NEBIUS_API_KEY"],
)
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
tavily_calls = 0

SYSTEM = (
    "You are a security research agent. Use lookup_cve_severity for CVSS and "
    "severity facts. Use web_search for current facts such as fixed versions "
    "and advisories. Never answer these from memory. Cite source URLs."
)

# ---------- Tools (plain Python; our code runs them, never the model) ----------
CVE_DB = {
    "CVE-2021-44228": {"name": "Log4Shell", "cvss": 10.0, "severity": "Critical"},
    "CVE-2014-0160": {"name": "Heartbleed", "cvss": 7.5, "severity": "High"},
}


def lookup_cve_severity(cve_id: str) -> dict:
    return CVE_DB.get(cve_id.upper(), {"error": f"{cve_id} not found"})


def web_search(query: str) -> dict:
    global tavily_calls
    tavily_calls += 1
    r = tavily.search(query=query, max_results=3)
    return {"results": [
        {"title": x["title"], "url": x["url"], "snippet": x["content"][:600]}
        for x in r["results"]
    ]}


TOOLS = [
    {"type": "function", "function": {
        "name": "lookup_cve_severity",
        "description": "Look up name, CVSS score and severity for a CVE id.",
        "parameters": {"type": "object",
                       "properties": {"cve_id": {"type": "string"}},
                       "required": ["cve_id"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the live web. Use for current facts, versions, advisories.",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
]
REGISTRY = {"lookup_cve_severity": lookup_cve_severity, "web_search": web_search}


def log_usage(resp, step):
    u = resp.usage
    d = getattr(u, "completion_tokens_details", None)
    reasoning = getattr(d, "reasoning_tokens", None) if d else None
    cost = (u.prompt_tokens * PRICE_IN + u.completion_tokens * PRICE_OUT) / 1_000_000
    row = {"ts": time.time(), "script": "agent_v2", "model": MODEL, "step": step,
           "in": u.prompt_tokens, "out": u.completion_tokens, "reasoning": reasoning,
           "est_cost_usd": round(cost, 6), "tavily_calls_so_far": tavily_calls}
    with open("usage_log.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"  [step {step}] in={u.prompt_tokens} out={u.completion_tokens} "
          f"reasoning={reasoning} ~${cost:.5f}")


def run_tool(name, raw_args):
    """Run a tool safely. Errors go back to the model as data, never crash the loop."""
    try:
        args = json.loads(raw_args)
        if name not in REGISTRY:
            return {"error": f"unknown tool {name}"}
        return REGISTRY[name](**args)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def run_agent(question: str):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": question}]
    for step in range(1, MAX_STEPS + 1):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=MAX_TOKENS,
        )
        log_usage(resp, step)
        choice = resp.choices[0]
        msg = choice.message

        if choice.finish_reason == "length":
            print("STOP: hit max_tokens (reasoning likely ate the budget).")
            return

        if msg.tool_calls:
            print(f"  model requested {len(msg.tool_calls)} tool call(s) this step")
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                print(f"  -> {tc.function.name}({tc.function.arguments})")
                result = run_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result)})
            continue

        if not msg.content:
            print("STOP: empty content (check reasoning budget).")
            return
        print("\nFINAL ANSWER:\n" + msg.content)
        print(f"\n(tavily calls used: {tavily_calls})")
        return

    print("STOP: MAX_STEPS reached without a final answer.")


if __name__ == "__main__":
    run_agent("For Log4Shell, what is the CVSS score, and what is the current "
              "recommended fixed Log4j version? Cite sources.")
