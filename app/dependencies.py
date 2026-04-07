from __future__ import annotations

import functools
from pathlib import Path

from app.repositories.sqlite_blocks import SQLiteBlockRepository

_BASE_DIR = Path(__file__).resolve().parent.parent
_DB_FILE = _BASE_DIR / "data" / "blocks.sqlite3"


@functools.cache
def get_repository() -> SQLiteBlockRepository:
  repo = SQLiteBlockRepository(_DB_FILE)
  repo.initialize()
  return repo
