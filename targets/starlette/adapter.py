"""Adapter: the model's entry point into the REAL Starlette StaticFiles.

read_user_file(user_input) hands user_input straight to the pip-installed
starlette.staticfiles.StaticFiles.lookup_path and returns the file it resolves to.
The traversal decision is made entirely by Starlette (commonprefix on <0.27.0,
commonpath on >=0.27.0); this file only translates 'resolved outside' into an error,
so a leak shows up as the canary in stdout and a block shows up as a crash.
No server, no ASGI, no event loop — lookup_path is a plain synchronous method.
"""
from starlette.staticfiles import StaticFiles

BASE_DIR = "/app/static"  # overridden only by the local build-time confirm


def read_user_file(user_input):
    sf = StaticFiles(directory=BASE_DIR)
    full_path, stat_result = sf.lookup_path(user_input)
    if not full_path or stat_result is None:
        raise PermissionError("blocked: resolved outside the static directory")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()
