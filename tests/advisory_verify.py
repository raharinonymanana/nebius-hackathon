"""Offline checks for prover/advisory.py. Zero Tavily credits, zero model calls.

Every case injects a fake client (client=FakeTavilyClient()) — no real TavilyClient,
no network, no .env. We also stub costlog.log_tavily_call to a no-op so the suite does
not write fake rows into the real usage_log.jsonl.

Run: python -m tests.advisory_verify
"""
import sys

from prover import advisory, costlog

costlog.log_tavily_call = lambda **kwargs: None  # keep the real cost log clean

GHSA = "https://github.com/advisories/GHSA-v5gw-mw7f-84px"
OSV = "https://osv.dev/vulnerability/GHSA-v5gw-mw7f-84px"
NVD = "https://nvd.nist.gov/vuln/detail/CVE-2023-29159"   # canonical detail (constructed)
# What Tavily actually returned on the real probe: a NON-advisory search URL -> discarded.
NVD_SEARCH = "https://nvd.nist.gov/vuln/search?results=records&query=CVE-2023-29159"
NEAAM = "https://github.com/NeaamHariri/devsec-benchmark/blob/main/BENCHMARK.md"

CANNED = {
    "query": "CVE-2023-29159 starlette StaticFiles path traversal",
    "request_id": "fake-req-0001",
    "response_time": 1.23,
    "results": [
        {"url": GHSA,
         "title": "Starlette has Path Traversal vulnerability in StaticFiles · CVE-2023-29159",
         "score": 0.93,
         "content": "Affected versions >= 0.13.5, < 0.27.0. Patched versions 0.27.0"},
        {"url": OSV,
         "title": "GHSA-v5gw-mw7f-84px - OSV",
         "score": 0.90,
         "content": "CVE-2023-29159 PYSEC-2023-83. Starlette path traversal in StaticFiles."},
        {"url": NVD_SEARCH,
         "title": "NVD - Search and Statistics",
         "score": 0.82,
         "content": "Directory traversal in Starlette >= 0.13.5 and prior to 0.27.0 allows ..."},
        {"url": NEAAM,
         "title": "devsec-benchmark/BENCHMARK.md",
         "score": 0.77,
         "content": "Path traversal Starlette CVE-2023-29159 fix 1797de4 sink staticfiles.py"},
    ],
    "usage": {"credits": 1},
}


class FakeTavilyClient:
    def search(self, *args, **kwargs):
        return {k: (list(v) if isinstance(v, list) else v) for k, v in CANNED.items()}


class FakeRaisingClient:
    def search(self, *args, **kwargs):
        raise RuntimeError("simulated Tavily failure")


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


results = []

res = advisory.lookup_advisory("CVE-2023-29159", "0.27.0", client=FakeTavilyClient())
cited = {c["url"] for c in res["cited_sources"]}
disc = {d["url"]: d["reason"] for d in res["discarded_sources"]}

results.append(check("1. cited_sources contains GHSA, OSV, NVD",
                     {GHSA, OSV, NVD} <= cited))
results.append(check("2. NeaamHariri discarded as path_not_advisory",
                     NEAAM not in cited and disc.get(NEAAM) == "path_not_advisory"))
results.append(check("3. advisory_consistent True for fixed 0.27.0",
                     res["advisory_consistent"] is True))

res_bad = advisory.lookup_advisory("CVE-2023-29159", "9.9.9", client=FakeTavilyClient())
results.append(check("4. advisory_consistent False for fixed 9.9.9",
                     res_bad["advisory_consistent"] is False))

raised = False
try:
    res_err = advisory.lookup_advisory("CVE-2023-29159", "0.27.0", client=FakeRaisingClient())
except Exception:  # noqa: BLE001
    raised = True
    res_err = None
results.append(check(
    "5. raising client -> error recorded, no crash",
    not raised and res_err is not None and res_err["error"]
    and res_err["cited_sources"] == [] and res_err["advisory_consistent"] is None))

# Case 6: the recall gap the live smoke hit — Tavily's NVD is a non-advisory search
# URL (discarded), but a CONSTRUCTED NVD detail URL must still land in cited_sources,
# while GHSA/OSV keep origin "tavily".
origins = {c["url"]: c.get("origin") for c in res["cited_sources"]}
disc6 = {d["url"] for d in res["discarded_sources"]}
results.append(check(
    "6. constructed NVD detail present; GHSA/OSV stay origin 'tavily'",
    origins.get(NVD) == "constructed"
    and NVD_SEARCH in disc6 and NVD_SEARCH not in origins
    and origins.get(GHSA) == "tavily" and origins.get(OSV) == "tavily"))

# Case 7: build_canonical_sources rejects a malformed id.
results.append(check("7. build_canonical_sources('not-a-cve') == []",
                     advisory.build_canonical_sources("not-a-cve") == []))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
