"""Hermes Project Dashboard: a local, zero-dependency status surface for LPOS.

The dashboard scans the Hermes root on disk (``LPOS_HERMES_ROOT``, default
``~/.hermes``), presents every project in one of four buckets (Active, Research,
Snoozed, Archive), and serves a single-page UI over a localhost-only stdlib
HTTP server.  All dashboard metadata lives in one JSON state file under
``<hermes-root>/dashboard/state.json``; project folders are never written to.

Run it with ``python -m lpos_engine.dashboard`` or through the ``lpos
dashboard`` CLI subcommand once wired.
"""

from __future__ import annotations

from .scanner import hermes_root, project_roots, scan_projects, search
from .server import DashboardApp, DashboardError, main, serve
from .state import BUCKETS, DashboardState

__all__ = [
    "BUCKETS",
    "DashboardApp",
    "DashboardError",
    "DashboardState",
    "hermes_root",
    "main",
    "project_roots",
    "scan_projects",
    "search",
    "serve",
]
