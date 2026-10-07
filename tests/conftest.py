"""Shared fixtures: v1-shaped API payloads, a client, and an HTTP mock."""

from collections.abc import Iterator
from typing import Any

import pytest
import respx

from todoist_cli.client import TodoistClient

BASE = "https://api.todoist.com/api/v1"


@pytest.fixture
def v1_task() -> Any:
    """Factory for task dicts shaped like the live v1 API."""

    def make(**overrides: Any) -> dict[str, Any]:
        task: dict[str, Any] = {
            "id": "t1",
            "content": "Write paper",
            "description": "",
            "priority": 1,
            "due": None,
            "deadline": None,
            "project_id": "p1",
            "section_id": None,
            "parent_id": None,
            "labels": [],
            "child_order": 3,
            "note_count": 2,
            "checked": False,
            "added_at": "2026-10-01T10:00:00Z",
            "added_by_uid": "u1",
        }
        task.update(overrides)
        return task

    return make


@pytest.fixture
def v1_project() -> dict[str, Any]:
    """A project dict shaped like the live v1 API."""
    return {"id": "p1", "name": "👥 Students", "color": "teal", "parent_id": None, "child_order": 1}


@pytest.fixture
def v1_section() -> dict[str, Any]:
    """A section dict shaped like the live v1 API."""
    return {"id": "s1", "name": "Sakshi", "project_id": "p1", "section_order": 2}


@pytest.fixture
def v1_label() -> dict[str, Any]:
    """A label dict shaped like the live v1 API."""
    return {"id": "l1", "name": "quick", "color": "green", "order": 1, "is_favorite": False}


@pytest.fixture
def api() -> Iterator[respx.MockRouter]:
    """HTTP mock rooted at the Todoist v1 base URL."""
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture
def client() -> Iterator[TodoistClient]:
    """A client with a dummy token."""
    with TodoistClient("x") as c:
        yield c
