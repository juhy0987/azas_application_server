# Projects Display Museum

FastAPI 기반의 3D 프로젝트 전시장 예시입니다.

- 메인 콘텐츠: Markdown 렌더링
- 지원 콘텐츠: 이미지, Notion 페이지 임베드
- UI: 카드 플립 기반 3D 갤러리

## Run

```bash
pip install -e .
uvicorn main:app --reload
```

브라우저에서 `http://127.0.0.1:8000` 접속

## Project Structure

```text
main.py
data/projects.json
templates/index.html
static/css/style.css
static/js/gallery.js
```

## Conventions

- Code: `docs/CODE_CONVENTION.md`
- GitHub: `.github/GITHUB_CONVENTION.md`
- Contribution Guide: `CONTRIBUTING.md`

## Data Format

`data/projects.json`에 전시 프로젝트를 배열로 저장합니다.

```json
[
	{
		"id": "p1",
		"title": "Project Title",
		"subtitle": "Project short description",
		"markdown": "# Markdown main content",
		"image_url": "https://...",
		"notion_url": "https://www.notion.so/..."
	}
]
```

`notion_url`은 공개 설정된 페이지일 때 임베드가 정상 동작합니다.
