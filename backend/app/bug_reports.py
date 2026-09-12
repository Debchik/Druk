from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile

from .auth import CurrentUser, current_user
from .db import SupabaseClient
from .errors import AppError

router = APIRouter(prefix="/api/v1")

_ALLOWED_SCREENSHOTS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
_MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024


@router.post("/bug-reports", status_code=201)
async def create_bug_report(
    description: str = Form(...),
    page_url: str = Form(""),
    user_agent: str = Form(""),
    screenshot: UploadFile | None = File(default=None),
    user: CurrentUser = Depends(current_user),
):
    text = description.strip()
    if not 3 <= len(text) <= 5000:
        raise AppError(422, "INVALID_BUG_REPORT", "Описание должно содержать от 3 до 5000 символов")

    db = SupabaseClient(user.token)
    screenshot_path: str | None = None

    if screenshot and screenshot.filename:
        content_type = (screenshot.content_type or "").lower()
        ext = _ALLOWED_SCREENSHOTS.get(content_type)
        if not ext:
            raise AppError(422, "INVALID_SCREENSHOT", "Поддерживаются PNG, JPG и WEBP")
        data = await screenshot.read(_MAX_SCREENSHOT_BYTES + 1)
        if len(data) > _MAX_SCREENSHOT_BYTES:
            raise AppError(413, "SCREENSHOT_TOO_LARGE", "Скриншот должен быть не больше 10 МБ")
        if not data:
            raise AppError(422, "INVALID_SCREENSHOT", "Скриншот пустой")
        screenshot_path = f"{user.workspace_id}/bug-reports/{uuid4()}.{ext}"
        await db.storage_upload(screenshot_path, data, content_type)

    try:
        rows = await db.insert(
            "bug_reports",
            {
                "workspace_id": user.workspace_id,
                "description": text,
                "page_url": page_url.strip()[:2000] or None,
                "user_agent": user_agent.strip()[:1000] or None,
                "screenshot_path": screenshot_path,
                "created_by": user.id,
            },
        )
    except Exception:
        if screenshot_path:
            try:
                await db.storage_delete([screenshot_path])
            except Exception:
                pass
        raise

    return rows[0]


@router.get("/bug-reports")
async def list_bug_reports(user: CurrentUser = Depends(current_user)):
    return await SupabaseClient(user.token).select(
        "bug_reports",
        filters={"workspace_id": user.workspace_id},
        order="created_at.desc",
        limit=100,
    )
