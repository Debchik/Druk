from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
import httpx
from fastapi import Header
from .config import get_settings
from .db import SupabaseClient, get_http_client
from .errors import AppError


@dataclass
class CurrentUser:
    id: str
    email: str | None
    workspace_id: str
    display_name: str
    token: str


# Auth is still fully checked by Supabase, but repeated requests from one browser
# reuse the verified identity/workspace for a short period. This matters when the
# FastAPI backend is used again after self-hosting.
_AUTH_CACHE_TTL = 30.0
_AUTH_CACHE_MAX = 256
_auth_cache: OrderedDict[str, tuple[float, CurrentUser]] = OrderedDict()


def _cache_key(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def _cached(token: str) -> CurrentUser | None:
    key = _cache_key(token)
    item = _auth_cache.get(key)
    if not item:
        return None
    expires, user = item
    if expires <= monotonic():
        _auth_cache.pop(key, None)
        return None
    _auth_cache.move_to_end(key)
    return user


def _remember(token: str, user: CurrentUser) -> None:
    key = _cache_key(token)
    _auth_cache[key] = (monotonic() + _AUTH_CACHE_TTL, user)
    _auth_cache.move_to_end(key)
    while len(_auth_cache) > _AUTH_CACHE_MAX:
        _auth_cache.popitem(last=False)


async def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Требуется вход")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError(401, "UNAUTHENTICATED", "Требуется вход")

    cached = _cached(token)
    if cached:
        return cached

    settings = get_settings()
    try:
        r = await get_http_client().get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": settings.supabase_publishable_key, "Authorization": f"Bearer {token}"},
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
    user = CurrentUser(uid, profile.get("email"), member["workspace_id"], member.get("display_name") or "Участник", token)
    _remember(token, user)
    return user
