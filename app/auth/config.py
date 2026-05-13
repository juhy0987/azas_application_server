"""관리자 인증 설정.

JWT (HS256) 기반 stateless 토큰 인증.

환경 변수:
  ADMIN_USERNAME      관리자 ID (기본 'admin')
  ADMIN_PASSWORD      관리자 비밀번호 (미설정 시 부팅마다 난수 — 경고 출력)
  JWT_SECRET          JWT 서명 비밀키 (미설정 시 프로세스마다 난수,
                      재기동 시 발급 토큰 전부 무효화 — 안정 운영을 위해 반드시 주입)
  JWT_EXPIRY_SECONDS  토큰 만료 시간 (기본 3600초)

Ref:
  https://fastapi.tiangolo.com/advanced/settings/
  https://datatracker.ietf.org/doc/html/rfc7519
  https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
"""
from __future__ import annotations

import os
import secrets
import sys

# 관리자 계정 자격 증명
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")

_password_from_env = os.getenv("ADMIN_PASSWORD")
if _password_from_env:
  ADMIN_PASSWORD: str = _password_from_env
else:
  ADMIN_PASSWORD = secrets.token_urlsafe(16)
  print(
    f"[WARNING] ADMIN_PASSWORD 환경변수가 설정되지 않았습니다. "
    f"임시 비밀번호가 생성되었습니다: {ADMIN_PASSWORD}",
    file=sys.stderr,
  )

# JWT 설정
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_SECONDS: int = int(os.getenv("JWT_EXPIRY_SECONDS", "3600"))

_jwt_secret_from_env = os.getenv("JWT_SECRET")
if _jwt_secret_from_env:
  JWT_SECRET: str = _jwt_secret_from_env
else:
  JWT_SECRET = secrets.token_urlsafe(32)
  print(
    "[WARNING] JWT_SECRET 환경변수가 설정되지 않았습니다. "
    "프로세스마다 난수 비밀키가 사용되어 재기동 시 모든 발급 토큰이 무효화됩니다.",
    file=sys.stderr,
  )
