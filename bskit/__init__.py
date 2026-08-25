"""bskit: the shared engine for Business Skill Kit.

Every skill runs on top of this. In fixture mode (the default, and the only mode wired
up in this repo) all reads and writes go against a synthetic company store, so a skill
can be tried and validated with zero real business data. A live mode would bind the same
operations to the first-party surface (the Dataverse MCP server, the Web API, the ERP
and Business Central tools); that binding is intentionally not shipped here.
"""
from .config import load_config
from .store import Store
from . import dryrun, report

__all__ = ["load_config", "Store", "dryrun", "report"]
