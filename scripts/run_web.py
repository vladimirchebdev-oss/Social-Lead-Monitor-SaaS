#!/usr/bin/env python3
"""Start the Social Lead Monitor web UI."""

from __future__ import annotations

import logging
import multiprocessing
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn

from db.schema import ensure_schema

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        if ensure_schema():
            print("Database schema applied from init.sql")
    except Exception as exc:
        print(f"Schema warning: {exc} (is PostgreSQL running?)")
    uvicorn.run(
        "web.app:app",
        host="localhost",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT / "web"), str(ROOT / "platforms"), str(ROOT / "db")],
    )
