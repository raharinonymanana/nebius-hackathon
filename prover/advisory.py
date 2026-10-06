"""Tavily advisory lookup (Brief 3a). CONTEXT ONLY.

Given a CVE id and the spec's FIXED_VERSION, do ONE live Tavily search, keep only
authoritative advisory URLs (domain pin + our own URL-path allowlist), string-check
that the fixed version is mentioned, and return a structured block for a receipt.

CRITICAL: advisory text is context only. Nothing here sets or influences a
PROVEN/NOT PROVEN verdict — that comes solely from agent_v4's replay harness. A failed
lookup degrades gracefully (error recorded) and must never crash a prove run.

Defense-in-depth on sources:
  * domain pin  -> Tavily include_domains + include_domains_mode="restrict" (their filter)
  * path allowlist -> our regexes below (ours); anything else is discarded, recorded.
"""
import os
import re
from datetime import datetime, timezone

from prover import costlog

AUTH_DOMAINS = ["github.com", "nvd.nist.gov", "osv.dev", "cve.org"]

# Second, independent filter: a result is kept ONLY if its URL matches one of these.
_ALLOWLIST = [
    re.compile(r"^https?://github\.com/advisories/GHSA-[\w-]+", re.I),
    re.compile(r"^https?://github\.com/[^/]+/[^/]+/security/advisories/GHSA-[\w-]+", re.I),
    re.compile(r"^https?://nvd\.nist\.gov/vuln/detail/CVE-[\d-]+", re.I),
    re.compile(r"^https?://osv\.dev/vulnerability/.+", re.I),
    re.compile(r"^https?://api\.osv\.dev/v1/vulns/.+", re.I),
    re.compile(r"^https?://(www\.)?cve\.org/CVERecord\?id=CVE-[\d-]+", re.I),
]


_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)


def _is_advisory_url(url: str) -> bool:
    return bool(url) and any(p.match(url) for p in _ALLOWLIST)


def build_canonical_sources(cve: str) -> list:
    """Canonical advisory URLs derived purely from a well-formed CVE id (NO network).

    These are canonical-by-construction, so they close recall gaps when Tavily returns
    a non-advisory URL (e.g. an NVD /vuln/search page) or omits a source entirely.
    Returns [] if cve does not match ^CVE-\\d{4}-\\d{4,}$."""
    if not cve or not _CVE_RE.match(cve):
        return []
    return [
        {"url": f"https://nvd.nist.gov/vuln/detail/{cve}",
         "origin": "constructed", "kind": "nvd"},
        {"url": f"https://www.cve.org/CVERecord?id={cve}",
         "origin": "constructed", "kind": "cve.org"},
    ]


def lookup_advisory(cve: str, fixed_version: str, *, client=None, extra_terms: str = "",
                    include_domains=AUTH_DOMAINS, max_results: int = 5,
                    timeout: float = 15) -> dict:
    """One live Tavily search for a CVE advisory, filtered to authoritative sources.

    client is injectable for offline tests. Returns a receipt-ready dict; on any Tavily
    error returns the same shape with error set (never raises)."""
    if client is None:
        from dotenv import load_dotenv
        from tavily import TavilyClient
        load_dotenv()
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])  # key never printed

    query = f"{cve} {extra_terms}".strip() or cve
    retrieved_at = datetime.now(timezone.utc).isoformat()  # RIGHT BEFORE the call

    base = {
        "provider": "tavily",
        "cve": cve,
        "query": query,
        "retrieved_at": retrieved_at,
        "fixed_version": fixed_version,
        "note": "advisory is context only; verdict comes from replay harness",
    }

    try:
        resp = client.search(
            query, search_depth="basic", max_results=max_results,
            include_domains=include_domains, include_domains_mode="restrict",
            include_usage=True, timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001  -- degrade, never crash a prove run
        costlog.log_tavily_call(cve=cve, query=query, credits=0)
        return {
            **base,
            "request_id": None,
            "response_time": None,
            "credits": None,
            "advisory_consistent": None,
            "cited_sources": [],
            "discarded_sources": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    cited_sources, discarded_sources = [], []
    consistent = False
    for r in (resp.get("results") or []):
        url = r.get("url")
        if _is_advisory_url(url):
            cited_sources.append({
                "url": url, "title": r.get("title"), "score": r.get("score"),
                "origin": "tavily",
            })
            haystack = f"{r.get('title') or ''}\n{r.get('content') or ''}"
            if fixed_version and fixed_version in haystack:
                consistent = True
        else:
            discarded_sources.append({"url": url, "reason": "path_not_advisory"})

    # Merge in canonical-by-construction URLs, de-duping by URL. A Tavily-returned
    # canonical URL keeps origin "tavily"; constructed ones only fill the gaps.
    seen = {c["url"] for c in cited_sources}
    for c in build_canonical_sources(cve):
        if c["url"] not in seen:
            cited_sources.append(c)
            seen.add(c["url"])

    credits = (resp.get("usage") or {}).get("credits")
    costlog.log_tavily_call(
        cve=cve, query=query, credits=credits,
        request_id=resp.get("request_id"), response_time=resp.get("response_time"),
    )

    return {
        **base,
        "request_id": resp.get("request_id"),
        "response_time": resp.get("response_time"),
        "credits": credits,
        "advisory_consistent": consistent,
        "cited_sources": cited_sources,
        "discarded_sources": discarded_sources,
        "error": None,
    }


if __name__ == "__main__":
    # Live smoke (spends ~1 Tavily credit). Prints only; writes no receipt; never the key.
    import json
    block = lookup_advisory(
        "CVE-2023-29159", "0.27.0",
        extra_terms="starlette StaticFiles path traversal",
    )
    print(json.dumps(block, indent=2, default=str))
