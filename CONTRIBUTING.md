# Contributing Guide

기여 전에 아래 문서를 먼저 확인해주세요.

- 코드 컨벤션: `docs/CODE_CONVENTION.md`
- GitHub 컨벤션: `.github/GITHUB_CONVENTION.md`

## Quick Start

1. 이슈를 생성하거나 기존 이슈를 확인합니다.
2. 규칙에 맞는 브랜치를 생성합니다.
3. 코드를 수정하고 로컬에서 동작을 확인합니다.
4. PR 템플릿에 맞춰 Pull Request를 생성합니다.

## Local Run

```bash
uv sync
uvicorn main:app --reload
```
