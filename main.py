from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "projects.json"

app = FastAPI(title="Projects Display Museum")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ProjectItem(BaseModel):
    """Represents one exhibition project card."""

    id: str
    title: str
    subtitle: str = ""
    markdown: str = ""
    image_url: str = ""
    notion_url: str = Field(default="")


def load_projects() -> list[ProjectItem]:
    """Load project items from local JSON data source."""

    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []

    projects: list[ProjectItem] = []
    for item in data:
        if isinstance(item, dict):
            projects.append(ProjectItem.model_validate(item))
    return projects


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the main 3D exhibition page."""

    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/projects", response_model=list[ProjectItem])
def list_projects() -> list[ProjectItem]:
    """Return all projects for gallery rendering."""

    return load_projects()
