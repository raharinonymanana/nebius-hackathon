import os, time, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url=os.environ["NEBIUS_BASE_URL"],
    api_key=os.environ["NEBIUS_API_KEY"],
)

# USD per 1M tokens (input, output). Source: Nebius Nemotron models page, 2026-09-30.
# Verify against console Billing > Prices.
PRICES = {
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.06, 0.24),
    "nvidia/Nemotron-3_5-Lightning": (0.06, 0.24),
    "nvidia/nemotron-3-super-120b-a12b": (0.30, 0.90),
    "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
}

def cost_usd(model_id, tokens_in, tokens_out):
    if model_id not in PRICES:
        return None
    p_in, p_out = PRICES[model_id]
    return (tokens_in * p_in + tokens_out * p_out) / 1_000_000

ids = sorted(m.id for m in client.models.list().data if "nemotron" in m.id.lower())
prompt = "In one sentence, what is the main daily task of a SOC analyst?"

for model_id in ids:
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
    except Exception as e:
        print(f"\n{model_id}\n  SKIPPED: {type(e).__name__}: {str(e)[:150]}")
        continue
    secs = round(time.time() - start, 2)
    u = r.usage
    details = getattr(u, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details else None
    cost = cost_usd(model_id, u.prompt_tokens, u.completion_tokens)
    cost_txt = f"${cost:.6f}" if cost is not None else "price unknown"
    print(f"\n{model_id}")
    print(f"  time: {secs}s | tokens in/out: {u.prompt_tokens}/{u.completion_tokens} | reasoning tokens: {reasoning} | cost: {cost_txt}")
    with open("usage_log.jsonl", "a") as f:
        f.write(json.dumps({"model": model_id, "secs": secs, "in": u.prompt_tokens,
                            "out": u.completion_tokens, "reasoning": reasoning,
                            "cost_usd": cost}) + "\n")
