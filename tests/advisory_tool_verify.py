"""Offline unit test for the search_advisory dispatch + cap. Zero credits, zero model
calls. We monkeypatch advisory.lookup_advisory to a stub (no network) and call the
dispatch handler directly — no real model, no real Tavily.

Run: python -m tests.advisory_tool_verify
"""
import sys

from prover import advisory
from prover import agent_v4 as a

# --- canned adv dict (shape matches the real lookup_advisory return) ----------------
CANNED_ADV = {
    "provider": "tavily",
    "cve": "CVE-2023-29159",
    "query": "CVE-2023-29159 starlette",
    "retrieved_at": "2026-10-06T00:00:00+00:00",
    "request_id": "fake-req-xyz",
    "response_time": 1.1,
    "credits": 1,
    "fixed_version": "0.27.0",
    "advisory_consistent": True,
    "cited_sources": [
        {"url": "https://github.com/advisories/GHSA-v5gw-mw7f-84px",
         "title": "Starlette StaticFiles path traversal", "score": 0.93, "origin": "tavily"},
        {"url": "https://nvd.nist.gov/vuln/detail/CVE-2023-29159",
         "origin": "constructed", "kind": "nvd"},
        {"url": "https://www.cve.org/CVERecord?id=CVE-2023-29159",
         "origin": "constructed", "kind": "cve.org"},
        {"url": "https://osv.dev/vulnerability/GHSA-v5gw-mw7f-84px",
         "title": "OSV entry", "score": 0.90, "origin": "tavily"},
    ],
    "discarded_sources": [
        {"url": "https://github.com/Someone/repo", "reason": "path_not_advisory"}],
    "error": None,
    "note": "advisory is context only; verdict comes from replay harness",
}

calls = {"n": 0}


def stub_lookup(cve, fixed_version, *, extra_terms="", **kwargs):
    calls["n"] += 1
    return dict(CANNED_ADV)


advisory.lookup_advisory = stub_lookup           # patch the module attr agent_v4 calls
a.advisory_tool_calls.clear()                    # fresh run state


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


results = []

# --- Case 1: first two calls dispatch for real, compact & filtered ------------------
r1 = a.search_advisory("CVE-2023-29159")
r2 = a.search_advisory("CVE-2023-29159", extra_terms="starlette path traversal")

compact_keys_ok = all(set(r) == {"cve", "advisory_consistent", "cited_sources", "note"}
                      for r in (r1, r2))
no_discarded = all("discarded_sources" not in r for r in (r1, r2))
cited_item_keys_ok = all(set(s.keys()) <= {"title", "url", "origin"}
                         for r in (r1, r2) for s in r["cited_sources"])
no_raw_content = all("content" not in s for r in (r1, r2) for s in r["cited_sources"])
top3 = all(len(r["cited_sources"]) <= 3 for r in (r1, r2))

results.append(check(
    "1. first two calls: compact dict, cited_sources present, no discarded/no raw content",
    compact_keys_ok and no_discarded and cited_item_keys_ok and no_raw_content and top3
    and len(a.advisory_tool_calls) == 2 and calls["n"] == 2))

# --- Case 2: third call hits the cap, no real lookup --------------------------------
r3 = a.search_advisory("CVE-2023-29159")
results.append(check(
    "2. third call: cap hit, list stays length 2, stub not called again",
    r3 == {"error": "advisory lookup limit reached", "calls_used": 2, "limit": 2}
    and len(a.advisory_tool_calls) == 2 and calls["n"] == 2))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
