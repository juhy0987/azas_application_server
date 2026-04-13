"""Mermaid 다이어그램 미리보기 기능 단위 테스트 (이슈 #60).

이슈 #60 에서 추가된 기능의 백엔드 검증 범위:
  1. Model 레이어   — 다양한 Mermaid 다이어그램 타입의 CodeBlock 모델 검증
  2. Repository 레이어 — 복잡한 다이어그램 코드의 저장/조회 왕복(round-trip) 검증
  3. API 레이어    — 미리보기에 필요한 응답 필드 구조 및 엣지 케이스 검증

프론트엔드(SVG 렌더링·크게 보기·다운로드)는 브라우저 환경에서만 실행 가능하므로
Python 단위 테스트에서는 해당 데이터를 올바르게 저장·제공하는 서버 측 동작을 검증한다.
"""
from __future__ import annotations

import pytest


# ── Mermaid 다이어그램 예시 ────────────────────────────────────────────────────

# 실제 서비스에서 자주 사용되는 대표 다이어그램 타입별 예시 소스
FLOWCHART_SRC = "graph TD\n  A[시작] --> B{조건}\n  B -- 예 --> C[처리]\n  B -- 아니오 --> D[종료]"
SEQUENCE_SRC = (
  "sequenceDiagram\n"
  "  participant 사용자\n"
  "  participant 서버\n"
  "  사용자->>서버: 로그인 요청\n"
  "  서버-->>사용자: 토큰 발급"
)
ER_SRC = (
  "erDiagram\n"
  "  USER ||--o{ ORDER : places\n"
  "  ORDER ||--|{ LINE-ITEM : contains\n"
  "  PRODUCT }|..|{ LINE-ITEM : includes"
)
CLASS_SRC = (
  "classDiagram\n"
  "  class Animal {\n"
  "    +String name\n"
  "    +move()\n"
  "  }\n"
  "  class Dog {\n"
  "    +bark()\n"
  "  }\n"
  "  Animal <|-- Dog"
)
GANTT_SRC = (
  "gantt\n"
  "  title 프로젝트 일정\n"
  "  section 기획\n"
  "    요구사항 분석: a1, 2024-01-01, 7d\n"
  "  section 개발\n"
  "    기능 구현: a2, after a1, 14d"
)
# 특수 문자 및 다국어 레이블 포함 다이어그램 — 직렬화 안전성 검증용
SPECIAL_CHAR_SRC = (
  "graph LR\n"
  '  A["사용자 <입력>"] --> B["API & 서버"]\n'
  '  B --> C["DB (SQLite)"]\n'
  "  C --> B"
)


# ── 1. Model 레이어 ───────────────────────────────────────────────────────────

class TestMermaidDiagramModel:
  """CodeBlock 모델이 다양한 Mermaid 다이어그램 타입의 소스를 올바르게 수락하는지 검증."""

  def _make(self, code: str) -> object:
    from app.models.blocks import CodeBlock
    return CodeBlock(id="test-id", type="code", code=code, language="mermaid")

  def test_flowchart_diagram_accepted(self):
    """flowchart(graph TD) 타입 다이어그램 소스를 저장할 수 있다."""
    block = self._make(FLOWCHART_SRC)
    assert block.language == "mermaid"
    assert block.code == FLOWCHART_SRC

  def test_sequence_diagram_accepted(self):
    """sequenceDiagram 타입 다이어그램 소스를 저장할 수 있다."""
    block = self._make(SEQUENCE_SRC)
    assert block.code == SEQUENCE_SRC

  def test_er_diagram_accepted(self):
    """erDiagram 타입 다이어그램 소스를 저장할 수 있다."""
    block = self._make(ER_SRC)
    assert block.code == ER_SRC

  def test_class_diagram_accepted(self):
    """classDiagram 타입 다이어그램 소스를 저장할 수 있다."""
    block = self._make(CLASS_SRC)
    assert block.code == CLASS_SRC

  def test_gantt_diagram_accepted(self):
    """gantt 타입 다이어그램 소스를 저장할 수 있다."""
    block = self._make(GANTT_SRC)
    assert block.code == GANTT_SRC

  def test_empty_diagram_source_accepted(self):
    """빈 문자열 소스도 허용된다 (프론트엔드가 빈 상태를 처리한다)."""
    block = self._make("")
    assert block.code == ""

  def test_special_characters_preserved(self):
    """꺾쇠·앰퍼샌드·괄호 등 특수 문자가 포함된 소스가 그대로 저장된다."""
    block = self._make(SPECIAL_CHAR_SRC)
    assert block.code == SPECIAL_CHAR_SRC

  def test_multiline_source_preserved(self):
    """개행 문자가 포함된 다중 행 소스가 손상 없이 저장된다."""
    multiline = "graph TD\n  A --> B\n  B --> C\n  C --> D"
    block = self._make(multiline)
    assert "\n" in block.code
    assert block.code == multiline


# ── 2. Repository 레이어 ──────────────────────────────────────────────────────

class TestMermaidDiagramRepository:
  """SQLiteBlockRepository 에서 Mermaid 다이어그램 데이터의 CRUD 를 검증."""

  def _create_mermaid_block(self, repo, code: str = FLOWCHART_SRC) -> tuple[dict, dict]:
    """테스트용 문서와 mermaid 코드 블록을 생성해 반환하는 헬퍼."""
    doc = repo.create_document()
    block = repo.create_block(doc["id"], "code")
    repo.update_block(block["id"], {"language": "mermaid", "code": code})
    return doc, block

  def test_flowchart_survives_roundtrip(self, repo):
    """flowchart 다이어그램 소스가 저장·조회 왕복 후 동일하게 반환된다."""
    doc, block = self._create_mermaid_block(repo, FLOWCHART_SRC)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == FLOWCHART_SRC

  def test_sequence_diagram_survives_roundtrip(self, repo):
    """sequenceDiagram 소스가 저장·조회 왕복 후 동일하게 반환된다."""
    doc, block = self._create_mermaid_block(repo, SEQUENCE_SRC)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == SEQUENCE_SRC

  def test_er_diagram_survives_roundtrip(self, repo):
    """erDiagram 소스가 저장·조회 왕복 후 동일하게 반환된다."""
    doc, block = self._create_mermaid_block(repo, ER_SRC)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == ER_SRC

  def test_special_characters_survive_roundtrip(self, repo):
    """특수 문자가 포함된 소스가 SQLite 저장 후에도 그대로 복원된다."""
    doc, block = self._create_mermaid_block(repo, SPECIAL_CHAR_SRC)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == SPECIAL_CHAR_SRC

  def test_large_diagram_survives_roundtrip(self, repo):
    """노드 수가 많은 대형 다이어그램 소스가 손실 없이 저장·복원된다."""
    nodes = "\n".join(f"  N{i} --> N{i + 1}" for i in range(100))
    large_src = f"graph TD\n{nodes}"
    doc, block = self._create_mermaid_block(repo, large_src)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == large_src

  def test_empty_diagram_source_survives_roundtrip(self, repo):
    """빈 소스("")가 저장·조회 후에도 빈 문자열로 반환된다."""
    doc, block = self._create_mermaid_block(repo, "")
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == ""
    assert fetched.blocks[0].language == "mermaid"

  def test_update_diagram_source_reflected(self, repo):
    """다이어그램 소스를 수정하면 변경 내용이 즉시 조회에 반영된다."""
    doc, block = self._create_mermaid_block(repo, FLOWCHART_SRC)
    repo.update_block(block["id"], {"code": SEQUENCE_SRC})
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].code == SEQUENCE_SRC

  def test_switch_diagram_type_via_code_update(self, repo):
    """소스 코드만 변경해 다이어그램 타입을 전환할 수 있다 (language 는 mermaid 유지)."""
    doc, block = self._create_mermaid_block(repo, FLOWCHART_SRC)
    repo.update_block(block["id"], {"code": ER_SRC})
    fetched = repo.get_document(doc["id"])
    b = fetched.blocks[0]
    # language 는 그대로 mermaid
    assert b.language == "mermaid"
    # code 는 ER 다이어그램으로 교체됨
    assert b.code == ER_SRC

  def test_multiple_mermaid_blocks_coexist(self, repo):
    """같은 문서에 여러 mermaid 블록이 각자 다른 소스로 공존할 수 있다."""
    doc = repo.create_document()
    b1 = repo.create_block(doc["id"], "code")
    b2 = repo.create_block(doc["id"], "code")
    repo.update_block(b1["id"], {"language": "mermaid", "code": FLOWCHART_SRC})
    repo.update_block(b2["id"], {"language": "mermaid", "code": SEQUENCE_SRC})

    fetched = repo.get_document(doc["id"])
    codes = {b.code for b in fetched.blocks}
    assert FLOWCHART_SRC in codes
    assert SEQUENCE_SRC in codes

  def test_language_field_is_mermaid_after_update(self, repo):
    """update_block 호출 후 language 필드가 "mermaid" 로 유지된다."""
    doc, block = self._create_mermaid_block(repo, FLOWCHART_SRC)
    fetched = repo.get_document(doc["id"])
    assert fetched.blocks[0].language == "mermaid"


# ── 3. API 레이어 ─────────────────────────────────────────────────────────────

class TestMermaidDiagramAPI:
  """HTTP API 를 통한 Mermaid 다이어그램 데이터의 저장·조회를 검증."""

  def _setup(self, client) -> tuple[dict, dict]:
    """mermaid 코드 블록이 있는 문서를 생성해 반환하는 헬퍼."""
    doc = client.post("/api/documents").json()
    block = client.post(
      f"/api/documents/{doc['id']}/blocks",
      json={"type": "code"},
    ).json()
    client.patch(f"/api/blocks/{block['id']}", json={"language": "mermaid"})
    return doc, block

  def test_get_document_includes_language_field(self, client):
    """GET /api/documents/{id} 응답 블록에 language 필드가 포함된다."""
    doc, _ = self._setup(client)
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert "language" in fetched["blocks"][0]

  def test_get_document_includes_code_field(self, client):
    """GET /api/documents/{id} 응답 블록에 code 필드가 포함된다."""
    doc, _ = self._setup(client)
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert "code" in fetched["blocks"][0]

  def test_patch_diagram_source_flowchart(self, client):
    """PATCH /api/blocks/{id} 로 flowchart 소스를 저장하면 200을 반환한다."""
    doc, block = self._setup(client)
    resp = client.patch(f"/api/blocks/{block['id']}", json={"code": FLOWCHART_SRC})
    assert resp.status_code == 200

  def test_patch_diagram_source_sequence(self, client):
    """PATCH /api/blocks/{id} 로 sequenceDiagram 소스를 저장하면 200을 반환한다."""
    doc, block = self._setup(client)
    resp = client.patch(f"/api/blocks/{block['id']}", json={"code": SEQUENCE_SRC})
    assert resp.status_code == 200

  def test_patch_diagram_source_er(self, client):
    """PATCH /api/blocks/{id} 로 erDiagram 소스를 저장하면 200을 반환한다."""
    doc, block = self._setup(client)
    resp = client.patch(f"/api/blocks/{block['id']}", json={"code": ER_SRC})
    assert resp.status_code == 200

  def test_diagram_source_reflected_in_get(self, client):
    """저장된 다이어그램 소스가 GET 응답에서 동일하게 반환된다."""
    doc, block = self._setup(client)
    client.patch(f"/api/blocks/{block['id']}", json={"code": FLOWCHART_SRC})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert fetched["blocks"][0]["code"] == FLOWCHART_SRC

  def test_special_characters_survive_api_roundtrip(self, client):
    """특수 문자가 포함된 소스가 API 왕복 후 손상 없이 반환된다."""
    doc, block = self._setup(client)
    client.patch(f"/api/blocks/{block['id']}", json={"code": SPECIAL_CHAR_SRC})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert fetched["blocks"][0]["code"] == SPECIAL_CHAR_SRC

  def test_multiline_diagram_survives_api_roundtrip(self, client):
    """개행 문자가 포함된 다중 행 소스가 API 왕복 후 동일하게 반환된다."""
    doc, block = self._setup(client)
    client.patch(f"/api/blocks/{block['id']}", json={"code": SEQUENCE_SRC})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    # 개행 문자가 보존되었는지 확인
    assert "\n" in fetched["blocks"][0]["code"]
    assert fetched["blocks"][0]["code"] == SEQUENCE_SRC

  def test_language_remains_mermaid_after_code_update(self, client):
    """code 만 업데이트해도 language 가 "mermaid" 로 유지된다."""
    doc, block = self._setup(client)
    client.patch(f"/api/blocks/{block['id']}", json={"code": ER_SRC})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert fetched["blocks"][0]["language"] == "mermaid"

  def test_update_diagram_source_sequential(self, client):
    """소스를 두 번 연속으로 업데이트하면 마지막 값이 반영된다."""
    doc, block = self._setup(client)
    client.patch(f"/api/blocks/{block['id']}", json={"code": FLOWCHART_SRC})
    client.patch(f"/api/blocks/{block['id']}", json={"code": CLASS_SRC})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert fetched["blocks"][0]["code"] == CLASS_SRC

  def test_empty_code_accepted_by_api(self, client):
    """빈 code 값("")을 PATCH 해도 200을 반환하고 빈 문자열로 저장된다."""
    doc, block = self._setup(client)
    resp = client.patch(f"/api/blocks/{block['id']}", json={"code": ""})
    assert resp.status_code == 200
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    assert fetched["blocks"][0]["code"] == ""

  def test_existing_python_block_unaffected(self, client):
    """mermaid 기능 추가 후에도 Python 언어 코드 블록이 정상 동작한다."""
    doc = client.post("/api/documents").json()
    block = client.post(
      f"/api/documents/{doc['id']}/blocks",
      json={"type": "code"},
    ).json()
    client.patch(f"/api/blocks/{block['id']}", json={"language": "python", "code": "print('hello')"})
    fetched = client.get(f"/api/documents/{doc['id']}").json()
    b = fetched["blocks"][0]
    assert b["language"] == "python"
    assert b["code"] == "print('hello')"
