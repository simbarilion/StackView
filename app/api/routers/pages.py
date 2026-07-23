"""Страницы лендинга (Jinja2)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing(request: Request) -> HTMLResponse:
    """Главная страница лендинга разработчика с формой обратной связи."""
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "pages/landing.html",
        {
            "app_name": settings.app_name,
            "environment": settings.app_env,
        },
    )
