"""Seeded target — VULNERABLE branch (faithful to Starlette CVE-2023-29159).

Containment check uses os.path.commonprefix (plain string prefix). A SIBLING whose
path string-starts-with the base dir slips through: '../static_secret.txt' resolves
to '/app/static_secret.txt', and commonprefix(['/app/static_secret.txt', '/app/static'])
== '/app/static' == base, so the check wrongly passes and the sibling leaks.
"""
import os

BASE_DIR = "/app/static"


def read_user_file(filename):
    base = os.path.realpath(BASE_DIR)
    full = os.path.realpath(os.path.join(base, filename))
    # VULN: compares letters, not folders.
    if os.path.commonprefix([full, base]) != base:
        raise PermissionError(f"outside static dir: {filename}")
    with open(full, encoding="utf-8") as f:
        return f.read()
