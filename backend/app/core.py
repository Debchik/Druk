from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4
import asyncio
import httpx
from fastapi import Depends, FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .auth import CurrentUser, current_user
from .config import get_settings
from .db import SupabaseClient
from .errors import AppError, app_error_handler
from .files import validate_file
from .schemas import (
    AnswerCreate, AnswerPatch, ChecklistCreate, DecisionCreate, FocusCreate,
    GithubRepoCreate, MeetingCreate, ProgramAnswerCreate, ProgramAnswerFromLibrary,
    ProgramAnswerPatch, ProgramCreate, ProgramPatch, SettingsPatch, TaskCreate, TaskPatch,
)

settings = get_settings()
app = FastAPI(title="Druk Internal Platform API", version="1.0.0")
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
_sync_locks: dict[str, asyncio.Lock] = {}


def db_for(user: CurrentUser) -> SupabaseClient:
    return SupabaseClient(user.token)


def dumped(model) -> tuple[dict, str | None]:
    data = model.model_dump(exclude_unset=True, mode="json")
    return data, data.pop("expected_updated_at", None)


async def one(db: SupabaseClient, table: str, user: CurrentUser, item_id: str, select: str = "*"):
    rows = await db.select(table, filters={"id": item_id, "workspace_id": user.workspace_id}, select=select, limit=1)
    if not rows:
        raise AppError(404, "NOT_FOUND", "Объект не найден")
    return rows[0]


async def patch_one(db: SupabaseClient, table: str, user: CurrentUser, item_id: str, data: dict, expected: str | None = None):
    filters = {"id": item_id, "workspace_id": user.workspace_id}
    if expected:
        filters["updated_at"] = expected
    rows = await db.patch(table, filters, data)
    if rows:
        return rows[0]
    exists = await db.select(table, filters={"id": item_id, "workspace_id": user.workspace_id}, select="id", limit=1)
    if exists and expected:
        raise AppError(409, "EDIT_CONFLICT", "Запись уже изменена. Обновите данные; введённый текст не отправляйте повторно вслепую.")
    raise AppError(404, "NOT_FOUND", "Объект не найден")


async def ensure_member(db: SupabaseClient, workspace_id: str, user_id: str | None):
    if not user_id:
        return
    rows = await db.select("workspace_members", filters={"workspace_id": workspace_id, "user_id": user_id}, select="user_id", limit=1)
    if not rows:
        raise AppError(422, "INVALID_ASSIGNEE", "Пользователь не является участником workspace")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/me")
async def me(user: CurrentUser = Depends(current_user)):
    return {"id": user.id, "email": user.email, "workspace_id": user.workspace_id, "display_name": user.display_name}


@app.get("/api/v1/members")
async def members(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("workspace_members", filters={"workspace_id": user.workspace_id}, select="user_id,display_name", order="display_name.asc")


@app.get("/api/v1/settings")
async def get_project_settings(user: CurrentUser = Depends(current_user)):
    rows = await db_for(user).select("project_settings", filters={"workspace_id": user.workspace_id}, limit=1)
    return rows[0] if rows else None


@app.patch("/api/v1/settings")
async def update_project_settings(body: SettingsPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    data, expected = dumped(body)
    if data.get("presentation_file_id"):
        await one(db, "files", user, data["presentation_file_id"], "id")
    filters = {"workspace_id": user.workspace_id}
    if expected:
        filters["updated_at"] = expected
    rows = await db.patch("project_settings", filters, data)
    if rows:
        return rows[0]
    existing = await db.select("project_settings", filters={"workspace_id": user.workspace_id}, limit=1)
    if existing and expected:
        raise AppError(409, "EDIT_CONFLICT", "Настройки уже изменены")
    created = await db.insert("project_settings", {"workspace_id": user.workspace_id, "project_name": data.get("project_name", "Друк"), "created_by": user.id, **data})
    return created[0]


@app.get("/api/v1/dashboard")
async def dashboard(user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    settings_rows, focus, tasks, programs, decisions = await asyncio.gather(
        db.select("project_settings", filters={"workspace_id": user.workspace_id}, limit=1),
        db.select("weekly_focus_items", filters={"workspace_id": user.workspace_id}, order="week_start.desc,created_at.asc", limit=6),
        db.select("tasks", filters={"workspace_id": user.workspace_id, "status": "neq.done"}, order="blocked.desc,due_date.asc.nullslast,created_at.desc", limit=12),
        db.select("programs", filters={"workspace_id": user.workspace_id, "archived": "eq.false"}, order="deadline.asc.nullslast", limit=8),
        db.select("decisions", filters={"workspace_id": user.workspace_id, "archived": "eq.false"}, order="decision_date.desc,created_at.desc", limit=5),
    )
    return {"settings": settings_rows[0] if settings_rows else None, "focus": focus, "tasks": tasks, "programs": programs, "decisions": decisions, "today": date.today().isoformat()}


@app.get("/api/v1/focus")
async def list_focus(week_start: date | None = None, user: CurrentUser = Depends(current_user)):
    filters = {"workspace_id": user.workspace_id}
    if week_start:
        filters["week_start"] = week_start.isoformat()
    return await db_for(user).select("weekly_focus_items", filters=filters, order="week_start.desc,created_at.asc")


@app.post("/api/v1/focus", status_code=201)
async def create_focus(body: FocusCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await ensure_member(db, user.workspace_id, body.assignee_id)
    existing = await db.select("weekly_focus_items", filters={"workspace_id": user.workspace_id, "week_start": body.week_start.isoformat()}, select="id")
    if len(existing) >= 3:
        raise AppError(422, "FOCUS_LIMIT", "На неделю можно задать не больше трёх результатов")
    return (await db.insert("weekly_focus_items", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}))[0]


@app.patch("/api/v1/focus/{item_id}")
async def update_focus(item_id: str, body: dict, user: CurrentUser = Depends(current_user)):
    data = {k: v for k, v in body.items() if k in {"text", "done", "assignee_id", "week_start"}}
    if "assignee_id" in data:
        await ensure_member(db_for(user), user.workspace_id, data["assignee_id"])
    return await patch_one(db_for(user), "weekly_focus_items", user, item_id, data)


@app.delete("/api/v1/focus/{item_id}", status_code=204)
async def delete_focus(item_id: str, user: CurrentUser = Depends(current_user)):
    if not await db_for(user).delete("weekly_focus_items", {"id": item_id, "workspace_id": user.workspace_id}):
        raise AppError(404, "NOT_FOUND", "Фокус не найден")


@app.get("/api/v1/tasks")
async def list_tasks(mine: bool = False, assignee_id: str | None = None, status: str | None = None, week_start: date | None = None, include_done: bool = False, user: CurrentUser = Depends(current_user)):
    filters: dict = {"workspace_id": user.workspace_id}
    if mine:
        filters["assignee_id"] = user.id
    elif assignee_id:
        filters["assignee_id"] = assignee_id
    if status:
        filters["status"] = status
    elif not include_done:
        filters["status"] = "neq.done"
    if week_start:
        filters["planned_week"] = week_start.isoformat()
    return await db_for(user).select("tasks", filters=filters, order="blocked.desc,due_date.asc.nullslast,created_at.desc")


@app.post("/api/v1/tasks", status_code=201)
async def create_task(body: TaskCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await ensure_member(db, user.workspace_id, body.assignee_id)
    return (await db.insert("tasks", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}))[0]


@app.patch("/api/v1/tasks/{item_id}")
async def update_task(item_id: str, body: TaskPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    data, expected = dumped(body)
    if "assignee_id" in data:
        await ensure_member(db, user.workspace_id, data["assignee_id"])
    return await patch_one(db, "tasks", user, item_id, data, expected)


@app.delete("/api/v1/tasks/{item_id}", status_code=204)
async def delete_task(item_id: str, user: CurrentUser = Depends(current_user)):
    if not await db_for(user).delete("tasks", {"id": item_id, "workspace_id": user.workspace_id}):
        raise AppError(404, "NOT_FOUND", "Задача не найдена")


@app.get("/api/v1/programs")
async def list_programs(status: str | None = None, include_archived: bool = False, q: str | None = None, user: CurrentUser = Depends(current_user)):
    filters: dict = {"workspace_id": user.workspace_id}
    if status:
        filters["status"] = status
    if not include_archived:
        filters["archived"] = "eq.false"
    rows = await db_for(user).select("programs", filters=filters, order="deadline.asc.nullslast,created_at.desc")
    if q:
        needle = " ".join(q.lower().split())
        rows = [r for r in rows if needle in " ".join((r.get("name") or "").lower().split())]
    return rows


@app.post("/api/v1/programs", status_code=201)
async def create_program(body: ProgramCreate, user: CurrentUser = Depends(current_user)):
    return (await db_for(user).insert("programs", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}))[0]


@app.get("/api/v1/programs/{program_id}")
async def get_program(program_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    program = await one(db, "programs", user, program_id)
    checklist, answers, links, submissions = await asyncio.gather(
        db.select("program_checklist_items", filters={"workspace_id": user.workspace_id, "program_id": program_id}, order="created_at.asc"),
        db.select("program_answers", filters={"workspace_id": user.workspace_id, "program_id": program_id}, order="created_at.asc"),
        db.select("program_file_links", filters={"workspace_id": user.workspace_id, "program_id": program_id}, select="id,file_id,files(id,display_name,original_name,mime_type,size_bytes,scope,created_at)", order="created_at.desc"),
        db.select("program_submissions", filters={"workspace_id": user.workspace_id, "program_id": program_id}, order="created_at.desc"),
    )
    return {"program": program, "checklist": checklist, "answers": answers, "files": links, "submissions": submissions}


@app.patch("/api/v1/programs/{program_id}")
async def update_program(program_id: str, body: ProgramPatch, user: CurrentUser = Depends(current_user)):
    data, expected = dumped(body)
    return await patch_one(db_for(user), "programs", user, program_id, data, expected)


@app.post("/api/v1/programs/{program_id}/checklist", status_code=201)
async def add_checklist(program_id: str, body: ChecklistCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await one(db, "programs", user, program_id, "id")
    return (await db.insert("program_checklist_items", {"workspace_id": user.workspace_id, "program_id": program_id, "text": body.text, "created_by": user.id}))[0]


@app.patch("/api/v1/checklist/{item_id}")
async def update_checklist(item_id: str, body: dict, user: CurrentUser = Depends(current_user)):
    return await patch_one(db_for(user), "program_checklist_items", user, item_id, {k: v for k, v in body.items() if k in {"text", "done"}})


@app.get("/api/v1/answers")
async def list_answers(q: str | None = Query(default=None, max_length=200), user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    if q and q.strip():
        return await db.rpc("search_answers", {"p_workspace_id": user.workspace_id, "p_query": q.strip()})
    return await db.select("answer_library", filters={"workspace_id": user.workspace_id}, order="updated_at.desc")


@app.post("/api/v1/answers", status_code=201)
async def create_answer(body: AnswerCreate, user: CurrentUser = Depends(current_user)):
    return (await db_for(user).insert("answer_library", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump()}))[0]


@app.patch("/api/v1/answers/{item_id}")
async def update_answer(item_id: str, body: AnswerPatch, user: CurrentUser = Depends(current_user)):
    data, expected = dumped(body)
    return await patch_one(db_for(user), "answer_library", user, item_id, data, expected)


@app.delete("/api/v1/answers/{item_id}", status_code=204)
async def delete_answer(item_id: str, user: CurrentUser = Depends(current_user)):
    if not await db_for(user).delete("answer_library", {"id": item_id, "workspace_id": user.workspace_id}):
        raise AppError(404, "NOT_FOUND", "Ответ не найден")


@app.post("/api/v1/programs/{program_id}/answers/from-library", status_code=201)
async def answer_from_library(program_id: str, body: ProgramAnswerFromLibrary, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await one(db, "programs", user, program_id, "id")
    source = await one(db, "answer_library", user, body.answer_id)
    payload = {"workspace_id": user.workspace_id, "program_id": program_id, "question": source["question"], "answer": source["answer"], "source_answer_id": source["id"], "created_by": user.id}
    return (await db.insert("program_answers", payload))[0]


@app.post("/api/v1/programs/{program_id}/answers", status_code=201)
async def create_program_answer(program_id: str, body: ProgramAnswerCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await one(db, "programs", user, program_id, "id")
    if body.source_answer_id:
        await one(db, "answer_library", user, body.source_answer_id, "id")
    return (await db.insert("program_answers", {"workspace_id": user.workspace_id, "program_id": program_id, "created_by": user.id, **body.model_dump()}))[0]


@app.patch("/api/v1/program-answers/{item_id}")
async def update_program_answer(item_id: str, body: ProgramAnswerPatch, user: CurrentUser = Depends(current_user)):
    data, expected = dumped(body)
    return await patch_one(db_for(user), "program_answers", user, item_id, data, expected)


@app.post("/api/v1/programs/{program_id}/submissions", status_code=201)
async def snapshot_submission(program_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    program = await one(db, "programs", user, program_id)
    answers, links = await asyncio.gather(
        db.select("program_answers", filters={"workspace_id": user.workspace_id, "program_id": program_id}, order="created_at.asc"),
        db.select("program_file_links", filters={"workspace_id": user.workspace_id, "program_id": program_id}, select="file_id,files(id,display_name,original_name,storage_path,mime_type,size_bytes)"),
    )
    snapshot = {"program": program, "answers": answers, "files": links}
    return (await db.insert("program_submissions", {"workspace_id": user.workspace_id, "program_id": program_id, "snapshot": snapshot, "created_by": user.id}))[0]


@app.get("/api/v1/files")
async def list_files(scope: str | None = None, q: str | None = None, user: CurrentUser = Depends(current_user)):
    filters = {"workspace_id": user.workspace_id}
    if scope:
        filters["scope"] = scope
    rows = await db_for(user).select("files", filters=filters, order="created_at.desc")
    if q:
        n = q.casefold().strip()
        rows = [r for r in rows if n in (r.get("display_name") or "").casefold()]
    return rows


@app.post("/api/v1/files", status_code=201)
async def upload_file(file: UploadFile = File(...), scope: str = Form("project"), program_id: str | None = Form(None), user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    data = await file.read(settings.max_file_size_mib * 1024 * 1024 + 1)
    _, mime = validate_file(file.filename or "file", data, settings.max_file_size_mib * 1024 * 1024)
    if scope not in {"project", "program"}:
        raise AppError(422, "INVALID_SCOPE", "Некорректная область файла")
    if scope == "program":
        if not program_id:
            raise AppError(422, "PROGRAM_REQUIRED", "Для файла программы нужна программа")
        await one(db, "programs", user, program_id, "id")
    file_id = str(uuid4())
    storage_path = f"{user.workspace_id}/{'programs/' + program_id if program_id else 'project'}/{file_id}"
    await db.storage_upload(storage_path, data, mime)
    try:
        created = await db.insert("files", {"id": file_id, "workspace_id": user.workspace_id, "scope": scope, "program_id": program_id, "storage_path": storage_path, "original_name": file.filename or "file", "display_name": file.filename or "file", "mime_type": mime, "size_bytes": len(data), "created_by": user.id})
    except Exception:
        try:
            await db.storage_delete([storage_path])
        finally:
            raise
    if program_id:
        await db.insert("program_file_links", {"workspace_id": user.workspace_id, "program_id": program_id, "file_id": file_id, "created_by": user.id})
    return created[0]


@app.post("/api/v1/files/{file_id}/signed-url")
async def signed_url(file_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    row = await one(db, "files", user, file_id)
    return {"url": await db.storage_sign(row["storage_path"], 300), "expires_in": 300}


@app.delete("/api/v1/files/{file_id}", status_code=204)
async def delete_file(file_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    row = await one(db, "files", user, file_id)
    refs = await db.select("program_submissions", filters={"workspace_id": user.workspace_id}, select="snapshot")
    if any(file_id in str(x.get("snapshot", "")) for x in refs):
        raise AppError(409, "FILE_IN_SUBMISSION", "Файл используется в зафиксированной заявке и не может быть удалён")
    await db.storage_delete([row["storage_path"]])
    await db.delete("files", {"id": file_id, "workspace_id": user.workspace_id})


@app.get("/api/v1/meetings")
async def meetings(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("meetings", filters={"workspace_id": user.workspace_id}, order="meeting_date.desc,created_at.desc")


@app.post("/api/v1/meetings", status_code=201)
async def create_meeting(body: MeetingCreate, user: CurrentUser = Depends(current_user)):
    return (await db_for(user).insert("meetings", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}))[0]


@app.get("/api/v1/decisions")
async def decisions(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("decisions", filters={"workspace_id": user.workspace_id, "archived": "eq.false"}, order="decision_date.desc,created_at.desc")


@app.post("/api/v1/decisions", status_code=201)
async def create_decision(body: DecisionCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    if body.meeting_id:
        await one(db, "meetings", user, body.meeting_id, "id")
    return (await db.insert("decisions", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump()}))[0]


async def fetch_github_issues(full_name: str) -> list[dict]:
    if not settings.github_token:
        raise AppError(422, "GITHUB_NOT_CONFIGURED", "GitHub token не настроен на backend")
    out: list[dict] = []
    page = 1
    headers = {"Authorization": f"Bearer {settings.github_token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            r = await client.get(f"https://api.github.com/repos/{full_name}/issues", headers=headers, params={"state": "all", "per_page": 100, "page": page})
            if r.status_code in {401, 403, 404}:
                raise AppError(r.status_code, "GITHUB_ERROR", "GitHub не дал доступ к репозиторию")
            if r.status_code >= 400:
                raise AppError(502, "GITHUB_ERROR", "Ошибка GitHub API")
            batch = r.json()
            for item in batch:
                if "pull_request" in item:
                    continue
                out.append({"github_id": item["id"], "number": item["number"], "title": item["title"], "state": item["state"], "url": item["html_url"], "assignee": (item.get("assignee") or {}).get("login"), "labels": [x.get("name") for x in item.get("labels", [])], "github_updated_at": item.get("updated_at")})
            if len(batch) < 100:
                break
            page += 1
    return out


@app.get("/api/v1/github/repositories")
async def github_repositories(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("github_repositories", filters={"workspace_id": user.workspace_id}, order="created_at.asc")


@app.post("/api/v1/github/repositories", status_code=201)
async def add_github_repository(body: GithubRepoCreate, user: CurrentUser = Depends(current_user)):
    return (await db_for(user).insert("github_repositories", {"workspace_id": user.workspace_id, "full_name": body.full_name, "created_by": user.id}))[0]


@app.post("/api/v1/github/repositories/{repo_id}/sync")
async def sync_github(repo_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    repo = await one(db, "github_repositories", user, repo_id)
    lock = _sync_locks.setdefault(repo_id, asyncio.Lock())
    if lock.locked():
        raise AppError(429, "SYNC_IN_PROGRESS", "Синхронизация уже выполняется")
    now = datetime.now(timezone.utc)
    last = repo.get("last_synced_at")
    if last:
        previous = datetime.fromisoformat(last.replace("Z", "+00:00"))
        if (now - previous).total_seconds() < settings.github_sync_cooldown_seconds:
            raise AppError(429, "SYNC_COOLDOWN", "Синхронизацию нельзя запускать так часто")
    async with lock:
        try:
            issues = await fetch_github_issues(repo["full_name"])
            for issue in issues:
                await db.insert("github_issues", {"workspace_id": user.workspace_id, "repository_id": repo_id, **issue}, on_conflict="github_id")
            await db.patch("github_repositories", {"id": repo_id, "workspace_id": user.workspace_id}, {"last_synced_at": now.isoformat(), "last_sync_error": None})
        except AppError as exc:
            await db.patch("github_repositories", {"id": repo_id, "workspace_id": user.workspace_id}, {"last_sync_error": exc.message})
            raise
    return {"ok": True, "count": len(issues), "synced_at": now.isoformat()}


@app.get("/api/v1/github/issues")
async def github_issues(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("github_issues", filters={"workspace_id": user.workspace_id}, order="github_updated_at.desc")


@app.get("/api/v1/export")
async def export_workspace(user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    tables = ["project_settings", "weekly_focus_items", "tasks", "programs", "program_checklist_items", "answer_library", "program_answers", "program_submissions", "files", "program_file_links", "meetings", "decisions", "github_repositories", "github_issues"]
    values = await asyncio.gather(*(db.select(t, filters={"workspace_id": user.workspace_id}) for t in tables))
    return {"version": 1, "exported_at": datetime.now(timezone.utc).isoformat(), "workspace_id": user.workspace_id, "data": dict(zip(tables, values)), "note": "Binary file contents are not included."}
