"""Readiness check for the bulk-edit skill: confirms the store and required tables exist."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402

REQUIRED = ['lead']

if __name__ == "__main__":
    sk.preflight_main(REQUIRED)
