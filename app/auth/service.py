"""인증 서비스 — 자격 증명 검증과 JWT 발급/검증을 담당한다.

비밀번호 비교에 ``secrets.compare_digest``를 사용해 타이밍 공격을 방지한다.
JWT 는 HS256 으로 서명하며 payload 는 sub(username) + iat + exp.

Ref:
  https://docs.python.org/3/library/secrets.html#secrets.compare_digest
  https://datatracker.ietf.org/doc/html/rfc7519
"""
from __future__ import annotations

import secrets
import time

import jwt

from app.auth.config import (
  ADMIN_PASSWORD,
  ADMIN_USERNAME,
  JWT_ALGORITHM,
  JWT_EXPIRY_SECONDS,
  JWT_SECRET,
)


def _encode(username: str) -> str:
  """username 으로 JWT access token 발급."""
  now = int(time.time())
  payload = {
    "sub": username,
    "iat": now,
    "exp": now + JWT_EXPIRY_SECONDS,
  }
  return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def authenticate(username: str, password: str) -> str | None:
  """자격 증명을 검증하고 JWT access token 을 반환한다.

  실패 시 None. 사용자명/비밀번호 모두 ``compare_digest`` 로 비교해
  어떤 필드가 틀렸는지 추론할 수 없게 한다.
  """
  username_ok = secrets.compare_digest(username, ADMIN_USERNAME)
  password_ok = secrets.compare_digest(password, ADMIN_PASSWORD)
  if not (username_ok and password_ok):
    return None
  return _encode(username)


def validate_session(token: str) -> str | None:
  """JWT 를 검증하고 username(sub) 을 반환한다. 무효/만료면 None."""
  try:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
  except jwt.PyJWTError:
    return None
  sub = payload.get("sub")
  if not isinstance(sub, str):
    return None
  return sub


def logout(token: str) -> bool:
  """JWT 는 stateless 라 서버 측 무효화 없음 — 클라이언트가 토큰을 폐기하면 충분.

  호환성 유지용 no-op. 항상 True 반환.
  블랙리스트 기반 강제 무효화가 필요해지면 여기에 구현.
  """
  return True
