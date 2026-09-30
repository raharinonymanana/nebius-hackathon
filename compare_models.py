import os, time, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    base_url=os.environ["NEBIUS_BASE_URL"],
    api_key=os.environ["NEBIUS_API_KEY"],
)

ids = sorted(m.id for m in client.models.list().data if "nemotron" in m.id.lower())
print("Nemotron models available:")
for i in ids:
    print("  -", i)

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
    reply = (r.choices[0].message.content or "").strip()
    print(f"\n{model_id}")
    print(f"  time: {secs}s | tokens in/out: {u.prompt_tokens}/{u.completion_tokens}")
    print(f"  reply: {reply[:300]}")
    with open("usage_log.jsonl", "a") as f:
        f.write(json.dumps({"model": model_id, "secs": secs,
                            "in": u.prompt_tokens, "out": u.completion_tokens}) + "\n")
