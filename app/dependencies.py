from __future__ import annotations

import functools
import os
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session

from app.models.orm import Base


def _build_db_url() -> URL:
  """환경변수에서 PostgreSQL 접속 정보를 조립한다.

  필수: DB_HOST, DB_USER, DB_PASS, DB_NAME
  선택: DB_PORT (기본 5432)
  """
  missing = [k for k in ("DB_HOST", "DB_USER", "DB_PASS", "DB_NAME") if not os.getenv(k)]
  if missing:
    raise RuntimeError(
      f"PostgreSQL 접속에 필요한 환경변수가 누락되었습니다: {', '.join(missing)}"
    )
  return URL.create(
    drivername="postgresql+psycopg2",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASS"],
    host=os.environ["DB_HOST"],
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.environ["DB_NAME"],
  )


def _migrate(engine: Engine) -> None:
  """create_all로 처리할 수 없는 추가 컬럼을 보정한다.

  PostgreSQL 9.6+의 ADD COLUMN IF NOT EXISTS를 사용하므로 기존 DB에서도
  안전하게 재실행할 수 있다.
  """
  with engine.connect() as conn:
    for ddl in (
      "ALTER TABLE documents ADD COLUMN IF NOT EXISTS parent_id TEXT",
      "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_block_id TEXT",
    ):
      conn.execute(text(ddl))
    conn.commit()


@functools.cache
def _get_engine() -> Engine:
  """엔진을 생성하고 스키마 초기화 및 시드를 1회 수행한다."""
  engine = create_engine(_build_db_url(), pool_pre_ping=True)
  Base.metadata.create_all(engine)
  _migrate(engine)
  from app.repositories.sqlite_blocks import SQLiteBlockRepository
  with Session(engine) as session:
    SQLiteBlockRepository(session)._seed_if_empty()
  return engine


def get_session() -> Generator[Session, None, None]:
  """Yield a SQLAlchemy session for the duration of a single request."""
  with Session(_get_engine()) as session:
    yield session


def get_repository(session: Session = Depends(get_session)):
  from app.repositories.sqlite_blocks import SQLiteBlockRepository
  return SQLiteBlockRepository(session)
