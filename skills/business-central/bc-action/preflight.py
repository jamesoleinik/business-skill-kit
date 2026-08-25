"""Readiness check for the bc-action skill: confirms the store and required tables exist."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402

REQUIRED = ['bc_item']

if __name__ == "__main__":
    sk.preflight_main(REQUIRED)
