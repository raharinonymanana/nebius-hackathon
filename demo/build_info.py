"""Capture the build identity (Twelve-Factor: every release has a unique ID).

The single source of truth is git, read ONCE per deploy and frozen into
demo/build_info.json. The handler and the frontend both read that file; neither
shells out to git at runtime. A deploy must never ship without an identity, so
this script exits non-zero if git is missing or fails.

Run from the repo root:  python -m demo.build_info

version is `git describe --tags --always --dirty`:
  * "v1.0.0"               an exact tag
  * "v1.0.0-2-g3bbde87"    2 commits past the tag
  * "3bbde87"              no tag yet (--always short sha) -- expected today
  * "...-dirty"            uncommitted changes present
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OUT_PATH = HERE / "build_info.json"


def _git(*args):
    """Run git with an argument list (never shell=True) from the repo root and
    return its stdout, stripped. Raises CalledProcessError on a non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main():
    try:
        version = _git("describe", "--tags", "--always", "--dirty")
        commit = _git("rev-parse", "HEAD")
    except FileNotFoundError:
        sys.exit("build_info: git executable not found -- cannot stamp a build identity")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or f"exit {exc.returncode}"
        sys.exit(f"build_info: git failed ({' '.join(exc.cmd)}): {detail}")

    info = {
        "name": "melodie",
        "version": version,
        "commit": commit,
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    OUT_PATH.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
