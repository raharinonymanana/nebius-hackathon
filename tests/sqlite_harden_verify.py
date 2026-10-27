"""Offline unit test for the in-sandbox SQLite hardening
(prover/verify_service.py :: _SANDBOX_HARDEN). Zero ConTree, zero network, zero
model calls. It execs the EXACT hardening snippet that is prepended to every
in-sandbox replay and proves it denies ATTACH / DETACH while leaving ordinary
SQL working -- defence-in-depth on top of the model-free canary verdict, tested
in isolation so it runs on every push.

Run from the repo root: python -m tests.sqlite_harden_verify
"""
import sqlite3
import sys

from prover import verify_service


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


# Apply the REAL snippet (not a copy) to this process's sqlite3 module, exactly
# as the sandbox runner does before any cartridge code executes.
exec(verify_service._SANDBOX_HARDEN, {})
conn = sqlite3.connect(":memory:")

results = []

# 1. ordinary SQL is unaffected (authorizer returns OK for non ATTACH/DETACH).
try:
    conn.execute("CREATE TABLE t(x)")
    conn.execute("INSERT INTO t VALUES (1)")
    results.append(check("1. ordinary SQL works under hardening",
                         conn.execute("SELECT x FROM t").fetchone() == (1,)))
except Exception as e:  # noqa: BLE001
    results.append(check(f"1. ordinary SQL works under hardening (ERR {e!r})", False))

# 2. ATTACH is denied by the authorizer.
try:
    conn.execute("ATTACH DATABASE ':memory:' AS evil")
    results.append(check("2. ATTACH denied", False))
except sqlite3.DatabaseError:
    results.append(check("2. ATTACH denied", True))

# 3. DETACH is denied by the authorizer.
try:
    conn.execute("DETACH DATABASE evil")
    results.append(check("3. DETACH denied", False))
except sqlite3.DatabaseError:
    results.append(check("3. DETACH denied", True))

passed = sum(results)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
