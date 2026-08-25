"""Configuration. No secrets in code: everything comes from the environment.

The environment URL and auth profile are read from `DATAVERSE_URL` and
`DATAVERSE_AUTH_PROFILE` (see .env.example). This repo ships fixture mode only, so no
value here ever reaches a real environment.
"""
import os


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_store_path():
    return os.path.join(repo_root(), "fixtures", "org.json")


def out_dir():
    d = os.path.join(repo_root(), "out")
    os.makedirs(d, exist_ok=True)
    return d


def load_config(store=None):
    """Read configuration from the environment. Returns fixture mode by default."""
    return {
        "url": os.environ.get("DATAVERSE_URL", ""),
        "profile": os.environ.get("DATAVERSE_AUTH_PROFILE", ""),
        "store": store or os.environ.get("BSKIT_STORE") or default_store_path(),
        "mode": "fixture",
    }
