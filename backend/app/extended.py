from __future__ import annotations

from datetime import date, time
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, HttpUrl

from .auth import CurrentUser, current_user
from .db import SupabaseClient
from .errors import AppError

router = APIRouter(prefix="/api/v1")


def db_for(user: CurrentUser) -> SupabaseClient:
    return SupabaseClient(user.token)


async def owned(db: SupabaseClient, table: str, user: CurrentUser, item_id: str):
    rows = await db.select(table, filters={"id": item_id, "workspace_id": user.workspace_id}, limit=1)
    if not rows:
        raise AppError(404, "NOT_FOUND", "Объект не найден")
    return rows[0]


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    meeting_date: date
    notes: str = ""
    start_time: time | None = None
    end_time: time | None = None
    event_type: Literal["meeting", "interview", "demo", "pitch", "webinar", "consultation", "deadline", "external"] = "meeting"
    mode: Literal["online", "offline"] = "online"
    location: str | None = Field(default=None, max_length=300)
    program_id: str | None = None
    participants: list[str] = Field(default_factory=list)


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    meeting_date: date | None = None
    notes: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    event_type: Literal["meeting", "interview", "demo", "pitch", "webinar", "consultation", "deadline", "external"] | None = None
    mode: Literal["online", "offline"] | None = None
    location: str | None = Field(default=None, max_length=300)
    program_id: str | None = None
    participants: list[str] | None = None


class LinkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    url: HttpUrl
    kind: Literal["landing", "telegram", "presentation", "other"] = "other"
    position: int = 0


class LinkPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    url: HttpUrl | None = None
    position: int | None = None


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(default="Участник", min_length=1, max_length=120)
    role: Literal["cofounder", "manager", "member", "guest"] = "member"


class MemberPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["cofounder", "manager", "member", "guest"] | None = None


class MetricCreate(BaseModel):
    metric_date: date = Field(default_factory=date.today)
    users_total: int = Field(default=0, ge=0)
    messages_total: int = Field(default=0, ge=0)
    dialogs_total: int = Field(default=0, ge=0)
    weekly_active: int = Field(default=0, ge=0)
    avg_session_seconds: int = Field(default=0, ge=0)
    retention_7d: float = Field(default=0, ge=0, le=100)
    registration_conversion: float = Field(default=0, ge=0, le=100)


class FeedbackCreate(BaseModel):
    quote: str = Field(min_length=1, max_length=2000)
    author_name: str = Field(min_length=1, max_length=120)
    author_role: str | None = Field(default=None, max_length=160)
    sentiment: Literal["positive", "constructive", "neutral"] = "positive"
    tags: list[str] = Field(default_factory=list, max_length=12)


class FileRename(BaseModel):
    display_name: str = Field(min_length=1, max_length=300)


class FileLink(BaseModel):
    file_id: str


CommentEntity = Literal["answer", "program_answer", "file"]
COMMENT_TABLES: dict[str, str] = {
    "answer": "answer_library",
    "program_answer": "program_answers",
    "file": "files",
}


class CommentCreate(BaseModel):
    entity_type: CommentEntity
    entity_id: str
    body: str = Field(min_length=1, max_length=10000)


class CommentPatch(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


async def ensure_comment_target(db: SupabaseClient, user: CurrentUser, entity_type: str, entity_id: str):
    table = COMMENT_TABLES.get(entity_type)
    if not table:
        raise AppError(422, "INVALID_COMMENT_TARGET", "Некорректный тип объекта комментария")
    await owned(db, table, user, entity_id)


@router.get("/comments")
async def list_comments(
    entity_type: CommentEntity = Query(...),
    entity_id: str = Query(...),
    user: CurrentUser = Depends(current_user),
):
    db = db_for(user)
    await ensure_comment_target(db, user, entity_type, entity_id)
    rows = await db.select(
        "entity_comments",
        filters={"workspace_id": user.workspace_id, "entity_type": entity_type, "entity_id": entity_id},
        order="created_at.asc",
    )
    members = await db.select(
        "workspace_members",
        filters={"workspace_id": user.workspace_id},
        select="user_id,display_name",
    )
    names = {row["user_id"]: row["display_name"] for row in members}
    for row in rows:
        row["author_name"] = names.get(row.get("created_by"), "Участник")
        row["can_edit"] = row.get("created_by") == user.id
    return rows


@router.post("/comments", status_code=201)
async def create_comment(body: CommentCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await ensure_comment_target(db, user, body.entity_type, body.entity_id)
    rows = await db.insert("entity_comments", {
        "workspace_id": user.workspace_id,
        "entity_type": body.entity_type,
        "entity_id": body.entity_id,
        "body": body.body.strip(),
        "created_by": user.id,
    })
    row = rows[0]
    row["author_name"] = user.display_name
    row["can_edit"] = True
    return row


@router.patch("/comments/{comment_id}")
async def patch_comment(comment_id: str, body: CommentPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    comment = await owned(db, "entity_comments", user, comment_id)
    if comment.get("created_by") != user.id:
        raise AppError(403, "COMMENT_FORBIDDEN", "Можно редактировать только свои комментарии")
    rows = await db.patch(
        "entity_comments",
        {"id": comment_id, "workspace_id": user.workspace_id, "created_by": user.id},
        {"body": body.body.strip()},
    )
    return rows[0]


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(comment_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    comment = await owned(db, "entity_comments", user, comment_id)
    if comment.get("created_by") != user.id:
        raise AppError(403, "COMMENT_FORBIDDEN", "Можно удалить только свой комментарий")
    await db.delete("entity_comments", {"id": comment_id, "workspace_id": user.workspace_id, "created_by": user.id})


@router.get("/team")
async def team(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select(
        "workspace_members",
        filters={"workspace_id": user.workspace_id},
        select="user_id,display_name,role",
        order="display_name.asc",
    )


@router.get("/analytics")
async def analytics(user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    metrics = await db.select(
        "product_metrics_daily",
        filters={"workspace_id": user.workspace_id},
        order="metric_date.desc",
        limit=31,
    )
    latest = metrics[0] if metrics else {
        "users_total": 0,
        "messages_total": 0,
        "dialogs_total": 0,
        "weekly_active": 0,
        "avg_session_seconds": 0,
        "retention_7d": 0,
        "registration_conversion": 0,
    }
    changes: dict[str, float] = {}
    if len(metrics) > 1:
        current, previous = metrics[0], metrics[min(len(metrics) - 1, 7)]
        for key in ("users_total", "messages_total", "dialogs_total", "weekly_active", "avg_session_seconds", "retention_7d", "registration_conversion"):
            a, b = float(current.get(key) or 0), float(previous.get(key) or 0)
            changes[key] = round(((a - b) / b) * 100, 1) if b else (100.0 if a else 0.0)
    latest["changes"] = changes
    feedback = await db.select("client_feedback", filters={"workspace_id": user.workspace_id}, order="created_at.desc", limit=20)
    return {"metric": latest, "history": list(reversed(metrics)), "feedback": feedback}


@router.post("/analytics/metrics", status_code=201)
async def create_metric(body: MetricCreate, user: CurrentUser = Depends(current_user)):
    payload = {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}
    rows = await db_for(user).insert("product_metrics_daily", payload, on_conflict="workspace_id,metric_date")
    return rows[0]


@router.post("/feedback", status_code=201)
async def create_feedback(body: FeedbackCreate, user: CurrentUser = Depends(current_user)):
    return (await db_for(user).insert("client_feedback", {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump()}))[0]


@router.get("/events")
async def list_events(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("meetings", filters={"workspace_id": user.workspace_id}, order="meeting_date.desc,start_time.asc.nullslast,created_at.desc")


@router.post("/events", status_code=201)
async def create_event(body: EventCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    if body.program_id:
        programs = await db.select("programs", filters={"id": body.program_id, "workspace_id": user.workspace_id}, select="id", limit=1)
        if not programs:
            raise AppError(422, "INVALID_PROGRAM", "Программа не найдена")
    payload = {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}
    return (await db.insert("meetings", payload))[0]


@router.patch("/events/{event_id}")
async def patch_event(event_id: str, body: EventPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await owned(db, "meetings", user, event_id)
    data = body.model_dump(exclude_unset=True, mode="json")
    rows = await db.patch("meetings", {"id": event_id, "workspace_id": user.workspace_id}, data)
    return rows[0]


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: str, user: CurrentUser = Depends(current_user)):
    rows = await db_for(user).delete("meetings", {"id": event_id, "workspace_id": user.workspace_id})
    if not rows:
        raise AppError(404, "NOT_FOUND", "Мероприятие не найдено")


@router.get("/links")
async def list_links(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("project_links", filters={"workspace_id": user.workspace_id}, order="position.asc,created_at.asc")


@router.post("/links", status_code=201)
async def create_link(body: LinkCreate, user: CurrentUser = Depends(current_user)):
    payload = {"workspace_id": user.workspace_id, "created_by": user.id, **body.model_dump(mode="json")}
    rows = await db_for(user).insert("project_links", payload, on_conflict="workspace_id,kind")
    return rows[0]


@router.patch("/links/{link_id}")
async def patch_link(link_id: str, body: LinkPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await owned(db, "project_links", user, link_id)
    rows = await db.patch("project_links", {"id": link_id, "workspace_id": user.workspace_id}, body.model_dump(exclude_unset=True, mode="json"))
    return rows[0]


@router.delete("/links/{link_id}", status_code=204)
async def delete_link(link_id: str, user: CurrentUser = Depends(current_user)):
    if not await db_for(user).delete("project_links", {"id": link_id, "workspace_id": user.workspace_id}):
        raise AppError(404, "NOT_FOUND", "Ссылка не найдена")


@router.get("/invites")
async def list_invites(user: CurrentUser = Depends(current_user)):
    return await db_for(user).select("workspace_invites", filters={"workspace_id": user.workspace_id, "status": "pending"}, order="created_at.desc")


@router.post("/invites", status_code=201)
async def create_invite(body: InviteCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    result = await db.rpc("add_workspace_member_by_email", {
        "p_workspace_id": user.workspace_id,
        "p_email": body.email.strip().lower(),
        "p_display_name": body.display_name.strip(),
        "p_role": body.role,
    })
    return result


@router.delete("/invites/{invite_id}", status_code=204)
async def delete_invite(invite_id: str, user: CurrentUser = Depends(current_user)):
    if not await db_for(user).delete("workspace_invites", {"id": invite_id, "workspace_id": user.workspace_id}):
        raise AppError(404, "NOT_FOUND", "Приглашение не найдено")


@router.patch("/members/{member_id}")
async def patch_member(member_id: str, body: MemberPatch, user: CurrentUser = Depends(current_user)):
    rows = await db_for(user).patch(
        "workspace_members",
        {"workspace_id": user.workspace_id, "user_id": member_id},
        body.model_dump(exclude_unset=True),
    )
    if not rows:
        raise AppError(404, "NOT_FOUND", "Участник не найден")
    return rows[0]


@router.patch("/files/{file_id}")
async def rename_file(file_id: str, body: FileRename, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await owned(db, "files", user, file_id)
    rows = await db.patch("files", {"id": file_id, "workspace_id": user.workspace_id}, {"display_name": body.display_name})
    return rows[0]


@router.post("/programs/{program_id}/files/link", status_code=201)
async def link_file_to_program(program_id: str, body: FileLink, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    programs = await db.select("programs", filters={"id": program_id, "workspace_id": user.workspace_id}, select="id", limit=1)
    files = await db.select("files", filters={"id": body.file_id, "workspace_id": user.workspace_id}, select="id", limit=1)
    if not programs or not files:
        raise AppError(404, "NOT_FOUND", "Программа или файл не найдены")
    rows = await db.insert("program_file_links", {"workspace_id": user.workspace_id, "program_id": program_id, "file_id": body.file_id, "created_by": user.id}, on_conflict="program_id,file_id")
    return rows[0]


@router.delete("/programs/{program_id}", status_code=204)
async def remove_program_from_list(program_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    programs = await db.patch("programs", {"id": program_id, "workspace_id": user.workspace_id}, {"archived": True})
    if not programs:
        raise AppError(404, "NOT_FOUND", "Программа не найдена")


@router.get("/search")
async def global_search(q: str = Query(min_length=2, max_length=120), user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    needle = q.casefold().strip()
    results: list[dict[str, Any]] = []
    tables = [
        ("tasks", "Задача", "/tasks", "title", "description"),
        ("programs", "Программа", "/programs/{id}", "name", "notes"),
        ("answer_library", "Ответ", "/answers", "question", "answer"),
        ("files", "Файл", "/files", "display_name", "original_name"),
        ("meetings", "Мероприятие", "/events", "title", "notes"),
        ("decisions", "Решение", "/events", "title", "text"),
    ]
    for table, label, href, title_key, extra_key in tables:
        rows = await db.select(table, filters={"workspace_id": user.workspace_id}, limit=100)
        for row in rows:
            hay = f"{row.get(title_key) or ''} {row.get(extra_key) or ''}".casefold()
            if needle in hay:
                results.append({
                    "id": row.get("id"),
                    "title": row.get(title_key) or label,
                    "type": table,
                    "type_label": label,
                    "href": href.format(id=row.get("id")),
                })
                if len(results) >= 30:
                    return {"results": results}
    return {"results": results}
