"""인증 관련 FastAPI 의존성.

라우터에서 ``Depends(require_admin)`` 으로 쓰기 권한을 보호한다.
``Authorization: Bearer <JWT>`` 헤더를 요구하며, 부재/만료 시 401 반환.

Ref:
  https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
  https://datatracker.ietf.org/doc/html/rfc6750
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import validate_session

# auto_error=False — 헤더 부재 시 직접 한국어 메시지로 응답
_bearer = HTTPBearer(auto_error=False)


def require_admin(
  credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
  """관리자 인증 여부를 확인하는 의존성.

  Authorization: Bearer <JWT> 헤더의 토큰을 검증.
  유효한 사용자의 username 을 반환한다.
  """
  if credentials is None or not credentials.credentials:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="로그인이 필요합니다.",
      headers={"WWW-Authenticate": "Bearer"},
    )
  username = validate_session(credentials.credentials)
  if username is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="세션이 만료되었습니다. 다시 로그인해 주세요.",
      headers={"WWW-Authenticate": "Bearer"},
    )
  return username
