"""Seeded target — FIXED branch. One swap vs vulnerable.py: commonprefix -> commonpath.

commonpath compares whole path components, so '/app/static_secret.txt' and '/app/static'
share only '/app' (the parent), not '/app/static' -> the sibling is correctly rejected.
This mirrors Starlette's real fix (commit 1797de4).
"""
import os

BASE_DIR = "/app/static"


def read_user_file(filename):
    base = os.path.realpath(BASE_DIR)
    full = os.path.realpath(os.path.join(base, filename))
    # FIX: compares folders, not letters.
    if os.path.commonpath([full, base]) != base:
        raise PermissionError(f"outside static dir: {filename}")
    with open(full, encoding="utf-8") as f:
        return f.read()
