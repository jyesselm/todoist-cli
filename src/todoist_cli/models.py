"""Pydantic models for Todoist entities and configuration."""

from datetime import datetime

from pydantic import BaseModel, Field


class DueDate(BaseModel):
    """Due date information for a task."""

    date: str  # YYYY-MM-DD
    string: str  # Human readable
    datetime: str | None = None  # RFC3339 if time specified
    timezone: str | None = None
    is_recurring: bool = False


class Task(BaseModel):
    """Todoist task model."""

    id: str
    content: str
    description: str = ""
    priority: int = Field(default=1, ge=1, le=4)
    due: DueDate | None = None
    project_id: str
    section_id: str | None = None
    parent_id: str | None = None
    labels: list[str] = Field(default_factory=list)
    order: int = 0
    comment_count: int = 0
    is_completed: bool = False
    deadline: str | None = None  # YYYY-MM-DD, separate from due
    created_at: str = ""
    creator_id: str = ""
    url: str = ""


class Project(BaseModel):
    """Todoist project model."""

    id: str
    name: str
    color: str = "grey"
    parent_id: str | None = None
    order: int = 0
    is_favorite: bool = False


class Section(BaseModel):
    """Todoist section model."""

    id: str
    name: str
    project_id: str
    order: int = 0


class Label(BaseModel):
    """Todoist label model."""

    id: str
    name: str
    color: str = "grey"
    order: int = 0
    is_favorite: bool = False


class Comment(BaseModel):
    """Todoist comment model."""

    id: str
    task_id: str | None = None
    project_id: str | None = None
    content: str
    posted_at: str


class ShortcutConfig(BaseModel):
    """Shortcut mappings for quick input."""

    labels: dict[str, str] = Field(default_factory=dict)  # w -> work
    projects: dict[str, str] = Field(default_factory=dict)  # i -> Inbox
    priorities: dict[str, str] = Field(default_factory=dict)  # u -> p1


class CachedData(BaseModel):
    """Cached API data stored in config."""

    projects: list[Project] = Field(default_factory=list)
    labels: list[Label] = Field(default_factory=list)
    last_sync: datetime | None = None


class Config(BaseModel):
    """Application configuration."""

    api_token: str = Field(alias="api-token")
    shortcuts: ShortcutConfig = Field(default_factory=ShortcutConfig)
    cached: CachedData = Field(default_factory=CachedData)

    model_config = {"populate_by_name": True}


class ParsedTask(BaseModel):
    """Result of parsing task content for Todoist syntax."""

    content: str  # Cleaned content without parsed elements
    labels: list[str] = Field(default_factory=list)
    project: str | None = None
    priority: int | None = None
    due_string: str | None = None
