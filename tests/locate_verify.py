"""Offline unit test for A2 'locate' measurement + handed-mode stability.
Zero credits, zero model calls. Tests the located_unaided LOGIC directly with crafted
inputs, and confirms the handed-mode prompt carries no locate instructions.

Run: python -m tests.locate_verify
"""
import os
import sys

from prover import advisory
from prover import agent_v4 as a

TF = "lookup_path"


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


results = []

# 1. handed mode -> located_unaided False regardless of who mentioned the function.
r1 = a._decide_located_unaided(TF, supplied_strings=["... lookup_path ..."],
                               model_strings=["I used lookup_path"],
                               mode_effective="handed")
results.append(check("1. handed mode -> located_unaided False",
                     r1["located_unaided"] is False))

# 2. locate mode, WE supplied the name -> False even if the model also said it.
r2 = a._decide_located_unaided(TF, supplied_strings=["advisory names lookup_path"],
                               model_strings=["found lookup_path"],
                               mode_effective="locate")
results.append(check("2. locate + we supplied name -> located_unaided False",
                     r2["advisory_named_function"] is True
                     and r2["model_identified_function"] is True
                     and r2["located_unaided"] is False))

# 3. locate mode, we did NOT supply it, model DID reference it -> True.
r3 = a._decide_located_unaided(TF, supplied_strings=["no function name here"],
                               model_strings=["I grepped and found lookup_path"],
                               mode_effective="locate")
results.append(check("3. locate + only model referenced -> located_unaided True",
                     r3["advisory_named_function"] is False
                     and r3["model_identified_function"] is True
                     and r3["located_unaided"] is True))

# 4. locate mode, neither mentioned it -> False.
r4 = a._decide_located_unaided(TF, supplied_strings=["nothing"],
                               model_strings=["nothing relevant"],
                               mode_effective="locate")
results.append(check("4. locate + neither -> located_unaided False",
                     r4["located_unaided"] is False))

# 5. handed-mode prompt unchanged: seeded spec (no CVE) must carry no locate text.
#    (module default SPEC is seeded; TASK_MODE_EFFECTIVE defaults to "handed")
handed_prompt = a.make_task()
results.append(check(
    "5. seeded handed prompt has no locate instructions",
    "LOCATE the specific function" not in handed_prompt
    and "You are NOT given the target's source" not in handed_prompt))

# --- gitpython locate: advisory-vs-scaffolding leak-guard scoping (TF = "clone_from") ---
# All offline: ADVISORY is populated from constructed sources or hand-crafted (no network).
GP_TF = "clone_from"
GP_SPEC_PATH = os.path.join(a._REPO_ROOT, "targets", "gitpython", "spec.py")
GP_CVE = "CVE-2022-24439"


def _route_gitpython_locate(adv):
    """Point the module at the gitpython spec in locate mode with a given ADVISORY (no
    network). Returns nothing; callers then assemble via a.make_task()."""
    a.SPEC = a.load_spec(GP_SPEC_PATH)
    a.TARGET_FUNCTION = getattr(a.SPEC, "TARGET_FUNCTION", None)
    a.TASK_MODE = "locate"
    a.TASK_MODE_EFFECTIVE = "locate"
    a.ADVISORY = adv


def _assemble():
    """Assemble the locate prompt; return (raised, prompt). raised=True on SystemExit."""
    try:
        return False, a.make_task()
    except SystemExit:
        return True, None


_CANONICAL_ADV = {
    "cve": GP_CVE, "fixed_version": "3.1.30", "advisory_consistent": False,
    "error": None, "cited_sources": advisory.build_canonical_sources(GP_CVE),
    "discarded_sources": [],
}

# 6. Canonical-only advisory (URLs, no titles): assembling does NOT raise and the prompt
#    does not contain the function name.
_route_gitpython_locate(_CANONICAL_ADV)
raised6, prompt6 = _assemble()
results.append(check(
    "6. canonical-only advisory -> no raise, name absent from prompt",
    raised6 is False and prompt6 is not None and GP_TF not in prompt6.lower()))

# 7. Advisory TITLE names the function (simulated Tavily title): assembling does NOT raise
#    (guard tolerates the advisory naming it), even though the name IS in the full prompt.
_TITLE_ADV = {
    "cve": GP_CVE, "fixed_version": "3.1.30", "advisory_consistent": True, "error": None,
    "cited_sources": [
        {"url": f"https://nvd.nist.gov/vuln/detail/{GP_CVE}",
         "title": "CVE-2022-24439: RCE in GitPython via Repo.clone_from ext URL",
         "origin": "tavily"},
    ],
    "discarded_sources": [],
}
_route_gitpython_locate(_TITLE_ADV)
raised7, prompt7 = _assemble()
results.append(check(
    "7. advisory title names it -> no raise, but name present in full prompt",
    raised7 is False and prompt7 is not None and GP_TF in prompt7.lower()))

# 8. SCAFFOLDING leak: force the name into a non-advisory part (SPEC.claim) -> MUST raise.
_route_gitpython_locate(_CANONICAL_ADV)
_orig_claim = a.SPEC.claim
a.SPEC.claim = lambda: "Leaky claim naming clone_from directly."
try:
    raised8, _ = _assemble()
finally:
    a.SPEC.claim = _orig_claim
results.append(check("8. scaffolding leak -> SystemExit", raised8 is True))

# 9. Booleans: advisory named it -> advisory_named_function True, located_unaided False.
r9 = a._decide_located_unaided(GP_TF,
                               supplied_strings=["...RCE in clone_from..."],
                               model_strings=["I triggered clone_from"],
                               mode_effective="locate")
results.append(check("9. advisory named it -> named True, located_unaided False",
                     r9["advisory_named_function"] is True
                     and r9["located_unaided"] is False))

# 10. Booleans: advisory silent + model found it -> named False, located_unaided True.
r10 = a._decide_located_unaided(GP_TF,
                                supplied_strings=["no name here"],
                                model_strings=["I located clone_from myself"],
                                mode_effective="locate")
results.append(check("10. advisory silent, model found -> named False, located_unaided True",
                     r10["advisory_named_function"] is False
                     and r10["located_unaided"] is True))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
