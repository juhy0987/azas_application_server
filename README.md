# projects_display

노션만으로 부족한 포트폴리오/프로젝트 공개 경험을 보완하기 위해 만든 블록 기반 전시 웹앱입니다.

## 한 줄 소개

문서-블록 트리 구조로 프로젝트를 스토리텔링하고, 이미지/중첩 페이지/재정렬 기능으로 "보여주기 좋은" 결과물을 빠르게 구성합니다.

## 왜 만들었나

- 노션의 표현 제약을 보완해 포트폴리오 전달력을 높이기 위해
- 프로젝트를 계층적으로 정리해 탐색성과 맥락 전달을 강화하기 위해

## 핵심 구현

- 문서 트리와 중첩 페이지(페이지 블록 생성 시 자식 문서 자동 생성)
- 다양한 블록 타입 편집(텍스트, 이미지, 컨테이너, 토글, 인용, 코드, 콜아웃, 구분선)
- 블록 순서 재배치 및 하위 트리 삭제/정합성 유지
- 이미지 업로드 시 WebP 압축 및 썸네일 자동 생성

## 기술 스택

- Backend: FastAPI, Pydantic v2, SQLAlchemy
- Frontend: Jinja2, Vanilla JavaScript, CSS
- Database: SQLite
- Runtime: Python 3.12+, uv, uvicorn
- Test: pytest, httpx, pytest-anyio

## 설계 포인트

- 계층 분리: Router / Repository / Model
- 패턴 적용: Repository Pattern, Dependency Injection, Discriminated Union
- 데이터 구조: parent 기반 Recursive Tree Mapping
- 무결성: 연관 생성 작업을 단일 트랜잭션으로 처리

## 실행 방법

```bash
uv sync
uvicorn main:app --reload
```

- Local: http://127.0.0.1:8000
- Test: `pytest -q`

## 배포 상태

- 도메인: TBD (아직 미할당)
- 현재는 배포 공간만 준비된 상태

## 문서

- 코드 컨벤션: docs/CODE_CONVENTION.md
- 기여 가이드: CONTRIBUTING.md
- GitHub 규칙: .github/GITHUB_CONVENTION.md
