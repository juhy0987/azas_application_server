"""관리자 인증 및 권한 제어 테스트 (JWT 기반).

검증 시나리오:
  1. 로그인 성공/실패 — access_token 발급
  2. 로그아웃 (클라이언트가 토큰을 폐기)
  3. 인증 상태 조회 (GET /api/auth/status)
  4. 미인증 쓰기 요청 차단 (401)
  5. Bearer 토큰으로 쓰기 요청 허용
  6. 만료 토큰 검증 실패
"""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.config import JWT_ALGORITHM, JWT_SECRET
from app.models.orm import Base
from app.repositories.sqlite_blocks import SQLiteBlockRepository


@pytest.fixture()
def engine():
  eng = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
  )
  Base.metadata.create_all(eng)
  return eng


@pytest.fixture()
def client(engine):
  """TestClient with in-memory DB injected via dependency override.

  주의: conftest.py 의 client 와 달리 이 fixture 는 자동 로그인을 하지 않는다.
  (각 테스트가 직접 인증 흐름을 검증해야 하므로)
  """
  from main import app
  from app.dependencies import get_repository

  def _override():
    with Session(engine) as s:
      yield SQLiteBlockRepository(s)

  app.dependency_overrides[get_repository] = _override
  with TestClient(app) as c:
    yield c
  app.dependency_overrides.clear()


def _login(client: TestClient, username: str = "admin", password: str = "admin1234") -> str:
  """로그인 헬퍼 — access_token 을 client 헤더에 설정하고 반환."""
  res = client.post("/api/auth/login", json={"username": username, "password": password})
  assert res.status_code == 200
  token = res.json()["access_token"]
  client.headers["Authorization"] = f"Bearer {token}"
  return token


def _logout_client(client: TestClient) -> None:
  """클라이언트 로컬에서 토큰을 폐기 (서버는 stateless 라 호출은 no-op)."""
  client.post("/api/auth/logout")
  client.headers.pop("Authorization", None)


# ── 로그인 테스트 ──────────────────────────────────────────────────────────

class TestLogin:
  def test_login_success(self, client: TestClient):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin1234"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "admin"
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and data["access_token"]
    assert data["expires_in"] > 0

  def test_login_wrong_password(self, client: TestClient):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert "올바르지 않습니다" in res.json()["detail"]

  def test_login_wrong_username(self, client: TestClient):
    res = client.post("/api/auth/login", json={"username": "hacker", "password": "admin1234"})
    assert res.status_code == 401

  def test_login_empty_credentials(self, client: TestClient):
    res = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert res.status_code == 401


# ── 로그아웃 테스트 ────────────────────────────────────────────────────────

class TestLogout:
  def test_logout_endpoint_returns_ok(self, client: TestClient):
    _login(client)
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["message"] == "로그아웃 완료"

  def test_status_after_client_drops_token(self, client: TestClient):
    _login(client)
    _logout_client(client)
    status = client.get("/api/auth/status")
    assert status.json()["authenticated"] is False

  def test_logout_without_session(self, client: TestClient):
    """헤더 없이 호출해도 에러 없이 200 응답."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200


# ── 인증 상태 조회 테스트 ──────────────────────────────────────────────────

class TestAuthStatus:
  def test_status_unauthenticated(self, client: TestClient):
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is False
    assert data["username"] is None

  def test_status_authenticated(self, client: TestClient):
    _login(client)
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert data["username"] == "admin"

  def test_status_invalid_token(self, client: TestClient):
    client.headers["Authorization"] = "Bearer not-a-jwt"
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    assert res.json()["authenticated"] is False


# ── 미인증 쓰기 차단 (401) ────────────────────────────────────────────────

class TestViewerWriteBlocked:
  """미인증 상태에서 모든 쓰기 엔드포인트가 401 을 반환하는지 검증."""

  def test_create_document_blocked(self, client: TestClient):
    res = client.post("/api/documents")
    assert res.status_code == 401

  def test_update_title_blocked(self, client: TestClient):
    res = client.patch("/api/documents/fake-id", json={"title": "test"})
    assert res.status_code == 401

  def test_create_block_blocked(self, client: TestClient):
    res = client.post("/api/documents/fake-id/blocks", json={"type": "text"})
    assert res.status_code == 401

  def test_delete_document_blocked(self, client: TestClient):
    res = client.delete("/api/documents/fake-id")
    assert res.status_code == 401

  def test_patch_block_blocked(self, client: TestClient):
    res = client.patch("/api/blocks/fake-id", json={"text": "hello"})
    assert res.status_code == 401

  def test_move_block_blocked(self, client: TestClient):
    res = client.patch("/api/blocks/fake-id/position", json={})
    assert res.status_code == 401

  def test_change_block_type_blocked(self, client: TestClient):
    res = client.patch("/api/blocks/fake-id/type", json={"type": "code"})
    assert res.status_code == 401

  def test_delete_block_blocked(self, client: TestClient):
    res = client.delete("/api/blocks/fake-id")
    assert res.status_code == 401

  def test_upload_image_blocked(self, client: TestClient):
    res = client.post("/api/upload", files={"file": ("test.png", b"fake", "image/png")})
    assert res.status_code == 401

  def test_database_patch_blocked(self, client: TestClient):
    res = client.patch("/api/database/blocks/fake-id", json={"title": "test"})
    assert res.status_code == 401

  def test_database_add_column_blocked(self, client: TestClient):
    res = client.post("/api/database/blocks/fake-id/schema/columns", json={"name": "col"})
    assert res.status_code == 401

  def test_database_remove_column_blocked(self, client: TestClient):
    res = client.delete("/api/database/blocks/fake-id/schema/columns/fake-col")
    assert res.status_code == 401


# ── 관리자 쓰기 허용 ───────────────────────────────────────────────────────

class TestAdminWriteAllowed:
  def test_create_document_allowed(self, client: TestClient):
    _login(client)
    res = client.post("/api/documents")
    assert res.status_code == 201
    assert "id" in res.json()

  def test_create_and_patch_block(self, client: TestClient):
    _login(client)
    doc = client.post("/api/documents").json()
    block = client.post(
      f"/api/documents/{doc['id']}/blocks",
      json={"type": "text"},
    ).json()
    res = client.patch(f"/api/blocks/{block['id']}", json={"text": "hello"})
    assert res.status_code == 200

  def test_delete_document_allowed(self, client: TestClient):
    _login(client)
    doc = client.post("/api/documents").json()
    res = client.delete(f"/api/documents/{doc['id']}")
    assert res.status_code == 204


# ── 토큰 만료 테스트 ───────────────────────────────────────────────────────

class TestTokenExpiry:
  def test_expired_token_blocks_write(self, client: TestClient):
    # 과거 시점에 만료된 JWT 를 직접 발급
    now = int(time.time())
    expired = jwt.encode(
      {"sub": "admin", "iat": now - 7200, "exp": now - 3600},
      JWT_SECRET,
      algorithm=JWT_ALGORITHM,
    )
    client.headers["Authorization"] = f"Bearer {expired}"
    res = client.post("/api/documents")
    assert res.status_code == 401
    assert "만료" in res.json()["detail"]

  def test_wrong_signature_blocks_write(self, client: TestClient):
    now = int(time.time())
    bogus = jwt.encode(
      {"sub": "admin", "iat": now, "exp": now + 3600},
      "wrong-secret",
      algorithm=JWT_ALGORITHM,
    )
    client.headers["Authorization"] = f"Bearer {bogus}"
    res = client.post("/api/documents")
    assert res.status_code == 401


# ── 로그아웃(클라이언트 토큰 폐기) 후 쓰기 차단 ────────────────────────────

class TestLogoutBlocksWrite:
  def test_write_blocked_after_logout(self, client: TestClient):
    _login(client)
    doc = client.post("/api/documents")
    assert doc.status_code == 201
    _logout_client(client)
    res = client.post("/api/documents")
    assert res.status_code == 401


# ── 읽기 API 접근 ──────────────────────────────────────────────────────────

class TestReadAccessAllowed:
  """미인증 상태에서도 읽기 API 는 정상 동작."""

  def test_list_documents_allowed(self, client: TestClient):
    res = client.get("/api/documents")
    assert res.status_code == 200

  def test_get_document_returns_404_not_401(self, client: TestClient):
    res = client.get("/api/documents/nonexistent")
    assert res.status_code == 404
