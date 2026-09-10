from dataclasses import dataclass
import httpx
from fastapi import Header
from .config import get_settings
from .db import SupabaseClient
from .errors import AppError


@dataclass
class CurrentUser:
    id: str
    email: str | None
    workspace_id: str
    display_name: str
    token: str


async def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Требуется вход")
    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as e:
            raise AppError(502, "AUTH_UNAVAILABLE", "Сервис авторизации временно недоступен") from e
    if r.status_code != 200:
        raise AppError(401, "INVALID_SESSION", "Сессия недействительна или истекла")
    profile = r.json()
    uid = profile.get("id")
    if not uid:
        raise AppError(401, "INVALID_SESSION", "Не удалось определить пользователя")
    db = SupabaseClient(token)
    rows = await db.select("workspace_members", filters={"user_id": uid}, select="workspace_id,display_name", limit=2)
    if not rows:
        raise AppError(403, "NOT_A_MEMBER", "У этого аккаунта нет доступа к рабочему пространству")
    if len(rows) > 1:
        raise AppError(409, "MULTIPLE_WORKSPACES", "Для MVP пользователь должен состоять только в одном workspace")
    member = rows[0]
    return CurrentUser(uid, profile.get("email"), member["workspace_id"], member.get("display_name") or "Участник", token)
