"""관리자 인증 설정.

환경 변수를 통해 관리자 자격 증명과 세션 정책을 설정한다.
설정이 누락된 경우 기본값을 사용하되, 프로덕션 환경에서는
반드시 ``ADMIN_PASSWORD``를 변경해야 한다.

Ref: https://fastapi.tiangolo.com/advanced/settings/
     https://docs.python.org/3/library/os.html#os.environ
"""
from __future__ import annotations

import os

# 관리자 계정 자격 증명
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin1234")

# 세션 정책
SESSION_COOKIE_NAME: str = "session_token"
SESSION_MAX_AGE: int = int(os.getenv("SESSION_MAX_AGE", "3600"))  # 기본 1시간(초)

# 쿠키 보안 설정
# Ref: https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#security
COOKIE_HTTPONLY: bool = True
COOKIE_SAMESITE: str = "lax"
# HTTPS 환경에서만 True로 설정 (개발 환경에서는 False)
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
