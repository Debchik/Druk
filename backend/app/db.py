from urllib.parse import quote
import httpx
from .config import get_settings
from .errors import AppError


class SupabaseClient:
    def __init__(self, token: str):
        self.settings = get_settings()
        self.token = token
        self.headers = {
            "apikey": self.settings.supabase_publishable_key,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def request(self, method: str, path: str, *, params=None, json=None, content=None, headers=None):
        all_headers = {**self.headers, **(headers or {})}
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                r = await client.request(
                    method,
                    f"{self.settings.supabase_url.rstrip('/')}{path}",
                    params=params,
                    json=json,
                    content=content,
                    headers=all_headers,
                )
            except httpx.HTTPError as e:
                raise AppError(502, "UPSTREAM_UNAVAILABLE", "Сервис данных временно недоступен") from e
        if r.status_code >= 400:
            message = "Ошибка доступа к данным"
            try:
                payload = r.json()
                message = payload.get("message") or payload.get("msg") or message
            except Exception:
                payload = {}
            raise AppError(r.status_code if r.status_code < 500 else 502, "SUPABASE_ERROR", message, payload if isinstance(payload, dict) else {})
        if not r.content:
            return None
        ctype = r.headers.get("content-type", "")
        return r.json() if "json" in ctype else r.content

    async def select(self, table: str, *, filters: dict | None = None, select="*", order=None, limit=None):
        params: list[tuple[str, str]] = [("select", select)]
        for k, v in (filters or {}).items():
            params.append((k, v if isinstance(v, str) and v.startswith(("eq.", "neq.", "in.", "is.", "gte.", "lte.")) else f"eq.{v}"))
        if order:
            params.append(("order", order))
        if limit:
            params.append(("limit", str(limit)))
        data = await self.request("GET", f"/rest/v1/{table}", params=params)
        return data or []

    async def insert(self, table: str, payload: dict | list[dict], *, on_conflict: str | None = None):
        params = {"on_conflict": on_conflict} if on_conflict else None
        prefer = "return=representation"
        if on_conflict:
            prefer += ",resolution=merge-duplicates"
        return await self.request("POST", f"/rest/v1/{table}", params=params, json=payload, headers={"Prefer": prefer})

    async def patch(self, table: str, filters: dict, payload: dict):
        params = {k: (v if isinstance(v, str) and v.startswith(("eq.", "neq.", "in.", "is.")) else f"eq.{v}") for k, v in filters.items()}
        return await self.request("PATCH", f"/rest/v1/{table}", params=params, json=payload, headers={"Prefer": "return=representation"})

    async def delete(self, table: str, filters: dict):
        params = {k: (v if isinstance(v, str) and v.startswith(("eq.", "in.")) else f"eq.{v}") for k, v in filters.items()}
        return await self.request("DELETE", f"/rest/v1/{table}", params=params, headers={"Prefer": "return=representation"})

    async def rpc(self, name: str, payload: dict):
        return await self.request("POST", f"/rest/v1/rpc/{name}", json=payload)

    async def storage_upload(self, path: str, data: bytes, mime: str):
        bucket = quote(self.settings.supabase_storage_bucket, safe="")
        encoded = "/".join(quote(part, safe="") for part in path.split("/"))
        return await self.request(
            "POST",
            f"/storage/v1/object/{bucket}/{encoded}",
            content=data,
            headers={"Content-Type": mime, "x-upsert": "false"},
        )

    async def storage_delete(self, paths: list[str]):
        return await self.request(
            "DELETE",
            f"/storage/v1/object/{quote(self.settings.supabase_storage_bucket, safe='')}",
            json={"prefixes": paths},
        )

    async def storage_sign(self, path: str, expires_in: int = 300) -> str:
        bucket = quote(self.settings.supabase_storage_bucket, safe="")
        encoded = "/".join(quote(part, safe="") for part in path.split("/"))
        data = await self.request("POST", f"/storage/v1/object/sign/{bucket}/{encoded}", json={"expiresIn": expires_in})
        signed = (data or {}).get("signedURL") or (data or {}).get("signedUrl")
        if not signed:
            raise AppError(502, "SIGNED_URL_FAILED", "Не удалось создать временную ссылку")
        if signed.startswith("http"):
            return signed
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1{signed}"
