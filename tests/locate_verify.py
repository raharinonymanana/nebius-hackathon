"""Offline unit test for A2 'locate' measurement + handed-mode stability.
Zero credits, zero model calls. Tests the located_unaided LOGIC directly with crafted
inputs, and confirms the handed-mode prompt carries no locate instructions.

Run: python -m tests.locate_verify
"""
import sys

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

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
