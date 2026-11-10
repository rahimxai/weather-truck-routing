import os

# Tests must pass on a fresh clone with no .env and no real secrets.
os.environ.setdefault("SECRET_KEY", "test-only-not-secret")

from .settings import *  # noqa: E402, F403
