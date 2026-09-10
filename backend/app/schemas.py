from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator

TaskStatus = Literal["planned", "in_progress", "done"]
ProgramStatus = Literal["considering", "preparing", "submitted", "next_stage", "accepted", "rejected"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: str | None = None
    status: TaskStatus = "planned"
    due_date: date | None = None
    planned_week: date | None = None
    blocked: bool = False
    block_reason: str | None = Field(default=None, max_length=500)


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: str | None = None
    status: TaskStatus | None = None
    due_date: date | None = None
    planned_week: date | None = None
    blocked: bool | None = None
    block_reason: str | None = Field(default=None, max_length=500)
    expected_updated_at: datetime | None = None


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    url: HttpUrl | None = None
    deadline: date | None = None
    status: ProgramStatus = "considering"
    next_step: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=20000)


class ProgramPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    url: HttpUrl | None = None
    deadline: date | None = None
    status: ProgramStatus | None = None
    next_step: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=20000)
    archived: bool | None = None
    expected_updated_at: datetime | None = None


class ChecklistCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class AnswerCreate(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(default="", max_length=50000)
    keywords: str = Field(default="", max_length=1000)


class AnswerPatch(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    answer: str | None = Field(default=None, max_length=50000)
    keywords: str | None = Field(default=None, max_length=1000)
    expected_updated_at: datetime | None = None


class ProgramAnswerCreate(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(default="", max_length=50000)
    source_answer_id: str | None = None


class ProgramAnswerFromLibrary(BaseModel):
    answer_id: str


class ProgramAnswerPatch(BaseModel):
    question: str | None = Field(default=None, max_length=1000)
    answer: str | None = Field(default=None, max_length=50000)
    expected_updated_at: datetime | None = None


class SettingsPatch(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    stage: str | None = Field(default=None, max_length=500)
    next_result: str | None = Field(default=None, max_length=1000)
    landing_url: HttpUrl | None = None
    telegram_url: HttpUrl | None = None
    presentation_file_id: str | None = None
    expected_updated_at: datetime | None = None

    @field_validator("telegram_url")
    @classmethod
    def validate_telegram(cls, value):
        if value and value.host not in {"t.me", "www.t.me"}:
            raise ValueError("Telegram ссылка должна вести на t.me")
        return value


class FocusCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    week_start: date
    assignee_id: str | None = None


class MeetingCreate(BaseModel):
    title: str = Field(default="Встреча", min_length=1, max_length=240)
    meeting_date: date
    notes: str = Field(default="", max_length=30000)


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, max_length=30000)
    meeting_id: str | None = None


class GithubRepoCreate(BaseModel):
    full_name: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)
