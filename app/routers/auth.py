"""관리자 인증 라우터.

엔드포인트:
  POST /api/auth/login   — 자격 증명 검증 후 JWT access token 발급
  POST /api/auth/logout  — (no-op, 클라이언트가 토큰을 폐기하면 됨)
  GET  /api/auth/status  — Bearer 토큰의 현재 인증 상태 조회

토큰 전송은 표준 ``Authorization: Bearer <JWT>`` 헤더 사용.
Ref:
  https://datatracker.ietf.org/doc/html/rfc6750
  https://datatracker.ietf.org/doc/html/rfc7519
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.config import JWT_EXPIRY_SECONDS
from app.auth.service import authenticate, logout, validate_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

# /status, /logout 에서 헤더 토큰 추출 (옵셔널 — 미보유 상태도 정상 응답)
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
  username: str
  password: str


class LoginResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"
  expires_in: int
  username: str


class StatusResponse(BaseModel):
  authenticated: bool
  username: str | None = None


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
  """관리자 로그인 — JWT access token 을 발급한다."""
  token = authenticate(body.username, body.password)
  if token is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="아이디 또는 비밀번호가 올바르지 않습니다.",
    )
  return LoginResponse(
    access_token=token,
    token_type="bearer",
    expires_in=JWT_EXPIRY_SECONDS,
    username=body.username,
  )


@router.post("/logout")
def do_logout(
  credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, str]:
  """관리자 로그아웃 — stateless JWT 라 서버 측 무효화 없음.

  클라이언트가 자신의 토큰 저장소(localStorage 등)에서 토큰을 폐기해야 한다.
  """
  if credentials and credentials.credentials:
    logout(credentials.credentials)
  return {"message": "로그아웃 완료"}


@router.get("/status", response_model=StatusResponse)
def auth_status(
  credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> StatusResponse:
  """현재 인증 상태를 반환한다."""
  if credentials is None or not credentials.credentials:
    return StatusResponse(authenticated=False)
  username = validate_session(credentials.credentials)
  if username is None:
    return StatusResponse(authenticated=False)
  return StatusResponse(authenticated=True, username=username)
