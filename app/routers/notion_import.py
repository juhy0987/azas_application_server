"""Notion Export Import API 라우터.

Notion에서 export한 파일(단일 .html / .md 또는 .zip 아카이브)을 업로드하면
프로젝트 페이지 구조로 자동 변환합니다.

엔드포인트:
  POST /api/import/notion — Notion HTML/Markdown/ZIP 파일 업로드 및 변환

Ref:
  - Notion Export 포맷: https://www.notion.so/help/export-your-content
  - FastAPI File Upload: https://fastapi.tiangolo.com/tutorial/request-files/
  - OWASP File Upload Cheat Sheet:
      https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import require_admin
from app.dependencies import get_repository
from app.repositories.sqlite_blocks import SQLiteBlockRepository
from app.services.image import process_image
from app.services.notion_import import (
  ImportResult,
  extract_and_parse_zip,
  parse_single_html,
  parse_single_markdown,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["import"])

# 업로드 크기 제한: 500 MB (Notion export ZIP은 대용량일 수 있음)
MAX_IMPORT_BYTES = 500 * 1024 * 1024

# 청크 단위 읽기 크기 (스트리밍 임시 파일에 기록)
CHUNK_SIZE = 64 * 1024

# Spool 임계치 — 이 크기까지는 메모리, 초과 시 자동으로 디스크 임시 파일에 보관
# Ref: Python tempfile.SpooledTemporaryFile —
#   https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile
SPOOL_MAX_MEMORY = 5 * 1024 * 1024  # 5 MB


# ── 응답 모델 ────────────────────────────────────────────────────────────────────

class ImportResponse(BaseModel):
  """Import 완료 응답 스키마."""

  document_id: str
  title: str
  total_pages: int
  report: dict[str, Any]


# ── Import 엔드포인트 ────────────────────────────────────────────────────────────

_ALLOWED_EXTS: tuple[str, ...] = (".html", ".htm", ".md", ".zip")


@router.post("/notion", status_code=201, response_model=ImportResponse)
async def import_notion(
  _admin: str = Depends(require_admin),
  file: UploadFile = File(...),
  repo: SQLiteBlockRepository = Depends(get_repository),
) -> ImportResponse:
  """Notion export 파일을 프로젝트 페이지로 변환 import합니다.

  지원 파일 형식:
    - .html — 단일 Notion HTML 페이지
    - .md   — 단일 Notion Markdown 페이지
    - .zip  — Notion export 아카이브 (HTML/Markdown + 이미지/CSV 포함)

  Returns:
    생성된 루트 문서 ID, 제목, 페이지 수, 변환 리포트.

  Raises:
    HTTPException 415: 지원하지 않는 파일 형식
    HTTPException 413: 파일 크기 초과
    HTTPException 422: 파싱 실패 / 빈 파일 / 변환할 페이지 없음
    HTTPException 500: 저장 실패
  """
  filename = file.filename or ""
  lower_name = filename.lower()

  if not any(lower_name.endswith(ext) for ext in _ALLOWED_EXTS):
    raise HTTPException(
      status_code=415,
      detail="지원하지 않는 파일 형식입니다. .html, .md 또는 .zip 파일을 업로드해주세요.",
    )

  data = await _read_upload_to_bytes(file)
  if not data:
    raise HTTPException(status_code=422, detail="빈 파일입니다.")

  # 파싱 단계 — ValueError는 사용자 제어 입력 검증 결과이므로 메시지 노출 OK,
  # 그 외 예외는 내부 정보 누출 방지를 위해 로그만 남기고 일반 메시지로 응답.
  try:
    if lower_name.endswith(".zip"):
      result = extract_and_parse_zip(data)
    elif lower_name.endswith(".md"):
      result = parse_single_markdown(data)
    else:
      result = parse_single_html(data)
  except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc))
  except Exception:
    logger.exception("Notion import 파싱 실패")
    raise HTTPException(
      status_code=422,
      detail="파일을 파싱하는 중 오류가 발생했습니다.",
    )

  if not result.pages:
    raise HTTPException(status_code=422, detail="변환할 페이지가 없습니다.")

  # DB 영속화 — 내부 예외는 클라이언트에 노출하지 않음
  try:
    image_resolver = _make_image_resolver(result.image_mappings)
    root_doc = repo.import_pages(result.pages, image_url_resolver=image_resolver)
  except Exception:
    logger.exception("Notion import 저장 실패")
    raise HTTPException(
      status_code=500,
      detail="가져온 데이터를 저장하는 중 오류가 발생했습니다.",
    )

  return ImportResponse(
    document_id=root_doc["id"],
    title=root_doc["title"],
    total_pages=len(result.pages),
    report=result.report.to_dict(),
  )


# ── 업로드 스트리밍 ─────────────────────────────────────────────────────────────

async def _read_upload_to_bytes(file: UploadFile) -> bytes:
  """업로드 파일을 청크 단위로 읽어 메모리 중복 없이 단일 bytes로 반환합니다.

  메모리 안전성:
    - SpooledTemporaryFile에 청크를 누적 기록 → 임계치(SPOOL_MAX_MEMORY)
      초과 시 자동으로 디스크로 spill되어 RSS 사용량 상한을 보장한다.
    - 최종적으로 bytes 한 카피만 만들어 반환하므로 list+join() 방식 대비
      피크 메모리가 절반 수준으로 낮아진다.

  Ref: tempfile.SpooledTemporaryFile —
    https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile
  """
  import tempfile

  total = 0
  with tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_MEMORY) as buf:
    while True:
      chunk = await file.read(CHUNK_SIZE)
      if not chunk:
        break
      total += len(chunk)
      if total > MAX_IMPORT_BYTES:
        raise HTTPException(
          status_code=413,
          detail=f"파일 크기가 {MAX_IMPORT_BYTES // (1024 * 1024)} MB를 초과합니다.",
        )
      buf.write(chunk)
    buf.seek(0)
    return buf.read()


# ── 이미지 처리 콜백 ────────────────────────────────────────────────────────────

def _make_image_resolver(
  image_mappings: dict[str, bytes],
) -> "callable[[dict[str, Any]], None]":
  """블록 트리 순회 중 호출되어 이미지 블록의 URL을 실제 저장 경로로 갱신한다.

  ZIP 내부 상대 경로(image_mappings 키)로 참조된 이미지는 process_image()를
  통해 서버에 저장하고, 블록의 url 필드를 갱신한다. 매핑에 없는 외부 URL은
  그대로 둔다.
  """
  def resolver(block: dict[str, Any]) -> None:
    url = block.get("url", "")
    if not url or url not in image_mappings:
      return
    try:
      processed = process_image(image_mappings[url])
      block["url"] = processed["url"]
    except Exception:
      logger.warning("이미지 업로드 실패: %s", url, exc_info=True)
      block["url"] = ""

  return resolver
