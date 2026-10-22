# -*- coding: utf-8 -*-
"""Giai quyet duong dan he thong (co the override bang env)."""
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = PKG_DIR.parent.parent


def state_dir() -> Path:
    env = os.environ.get("DNSENTINEL_STATE_DIR")
    if env:
        return Path(env)
    if Path("/var/lib/dnsentinel").exists():
        return Path("/var/lib/dnsentinel")
    return REPO_ROOT


def db_path() -> Path:
    env = os.environ.get("DNSENTINEL_DB")
    if env:
        return Path(env)
    return state_dir() / "dnsentinel.db"
