"""Todoist API v1 client (REST v2 was retired with a 410 in 2026)."""

from types import TracebackType
from typing import Any, Self

import httpx

from todoist_cli.models import Comment, DueDate, Label, Project, Section, Task


class _Unset:
    """Sentinel type: distinguishes "not passed" from an explicit None (clear)."""


UNSET = _Unset()


class TodoistError(Exception):
    """Base exception for Todoist API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TodoistClient:
    """Client for Todoist API v1."""

    BASE_URL = "https://api.todoist.com/api/v1"
    PAGE_SIZE = 200

    def __init__(self, api_token: str) -> None:
        """Initialize client with API token."""
        self._token = api_token
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30.0,
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make API request with error handling."""
        try:
            response = self._client.request(method, endpoint, params=params, json=json)
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            raise TodoistError(f"API error: {e.response.text}", e.response.status_code) from e
        except httpx.RequestError as e:
            raise TodoistError(f"Request failed: {e}") from e

    def _get_all(self, endpoint: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """GET a v1 list endpoint, following `next_cursor` until exhausted."""
        params = dict(params or {}, limit=self.PAGE_SIZE)
        items: list[dict[str, Any]] = []
        while True:
            page = self._request("GET", endpoint, params=params) or {}
            items.extend(page.get("results", []))
            cursor = page.get("next_cursor")
            if not cursor:
                return items
            params["cursor"] = cursor

    def _parse_task(self, data: dict[str, Any]) -> Task:
        """Parse task data from API response (v1 field names)."""
        due = None
        if data.get("due"):
            due = DueDate(**data["due"])

        return Task(
            id=data["id"],
            content=data["content"],
            description=data.get("description", ""),
            priority=data.get("priority", 1),
            due=due,
            project_id=data["project_id"],
            section_id=data.get("section_id"),
            parent_id=data.get("parent_id"),
            labels=data.get("labels", []),
            deadline=(data.get("deadline") or {}).get("date"),
            order=data.get("child_order", 0),
            comment_count=data.get("note_count", 0),
            is_completed=data.get("checked", False),
            created_at=data.get("added_at", ""),
            creator_id=data.get("added_by_uid", ""),
            url=f"https://app.todoist.com/app/task/{data['id']}",
        )

    def _parse_project(self, data: dict[str, Any]) -> Project:
        """Parse project data from API response (v1 field names)."""
        return Project(
            id=data["id"],
            name=data["name"],
            color=data.get("color", "grey"),
            parent_id=data.get("parent_id"),
            order=data.get("child_order", 0),
            is_favorite=data.get("is_favorite", False),
        )

    def _parse_section(self, data: dict[str, Any]) -> Section:
        """Parse section data from API response (v1 field names)."""
        return Section(
            id=data["id"],
            name=data["name"],
            project_id=data["project_id"],
            order=data.get("section_order", 0),
        )

    # ── Tasks ──────────────────────────────────────────────────────────────

    def get_tasks(
        self,
        filter: str | None = None,
        project_id: str | None = None,
        section_id: str | None = None,
        label: str | None = None,
    ) -> list[Task]:
        """Get active tasks with optional filtering.

        Args:
            filter: Todoist filter query (e.g., "today | overdue")
            project_id: Filter by project
            section_id: Filter by section
            label: Filter by label name
        """
        if filter:
            data = self._get_all("/tasks/filter", {"query": filter})
        else:
            params: dict[str, Any] = {}
            if project_id:
                params["project_id"] = project_id
            if section_id:
                params["section_id"] = section_id
            if label:
                params["label"] = label
            data = self._get_all("/tasks", params)
        return [self._parse_task(t) for t in data]

    def get_task(self, task_id: str) -> Task:
        """Get a single task by ID."""
        data = self._request("GET", f"/tasks/{task_id}")
        return self._parse_task(data)

    def create_task(
        self,
        content: str,
        description: str | None = None,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        labels: list[str] | None = None,
        priority: int | None = None,
        due_string: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            content: Task content (required)
            description: Extended description
            project_id: Target project (defaults to Inbox)
            section_id: Target section
            parent_id: Parent task ID for subtasks
            labels: List of label names
            priority: 1 (normal) to 4 (urgent)
            due_string: Natural language due date
            due_date: YYYY-MM-DD format
            due_datetime: RFC3339 datetime
        """
        payload: dict[str, Any] = {"content": content}

        if description:
            payload["description"] = description
        if project_id:
            payload["project_id"] = project_id
        if section_id:
            payload["section_id"] = section_id
        if parent_id:
            payload["parent_id"] = parent_id
        if labels:
            payload["labels"] = labels
        if priority:
            payload["priority"] = priority
        if due_string:
            payload["due_string"] = due_string
        if due_date:
            payload["due_date"] = due_date
        if due_datetime:
            payload["due_datetime"] = due_datetime

        data = self._request("POST", "/tasks", json=payload)
        return self._parse_task(data)

    def update_task(
        self,
        task_id: str,
        content: str | None = None,
        description: str | None = None,
        project_id: str | None = None,
        labels: list[str] | None = None,
        priority: int | None = None,
        due_string: str | None = None,
        due_date: str | None = None,
        deadline_date: str | None | _Unset = UNSET,
    ) -> Task:
        """Update an existing task. `deadline_date=None` clears the deadline."""
        payload: dict[str, Any] = {}

        if content is not None:
            payload["content"] = content
        if description is not None:
            payload["description"] = description
        if project_id is not None:
            payload["project_id"] = project_id
        if labels is not None:
            payload["labels"] = labels
        if priority is not None:
            payload["priority"] = priority
        if due_string is not None:
            payload["due_string"] = due_string
        if due_date is not None:
            payload["due_date"] = due_date
        if not isinstance(deadline_date, _Unset):
            payload["deadline_date"] = deadline_date

        data = self._request("POST", f"/tasks/{task_id}", json=payload)
        return self._parse_task(data)

    def close_task(self, task_id: str) -> None:
        """Complete/close a task."""
        self._request("POST", f"/tasks/{task_id}/close")

    def reopen_task(self, task_id: str) -> None:
        """Reopen a completed task."""
        self._request("POST", f"/tasks/{task_id}/reopen")

    def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        self._request("DELETE", f"/tasks/{task_id}")

    # ── Projects ───────────────────────────────────────────────────────────

    def get_projects(self) -> list[Project]:
        """Get all projects."""
        return [self._parse_project(p) for p in self._get_all("/projects")]

    def get_project(self, project_id: str) -> Project:
        """Get a single project by ID."""
        return self._parse_project(self._request("GET", f"/projects/{project_id}"))

    # ── Sections ───────────────────────────────────────────────────────────

    def get_sections(self, project_id: str | None = None) -> list[Section]:
        """Get sections, optionally restricted to one project."""
        params = {"project_id": project_id} if project_id else None
        return [self._parse_section(s) for s in self._get_all("/sections", params)]

    # ── Labels ─────────────────────────────────────────────────────────────

    def get_labels(self) -> list[Label]:
        """Get all labels."""
        data = self._get_all("/labels")
        return [
            Label(
                id=item["id"],
                name=item["name"],
                color=item.get("color", "grey"),
                order=item.get("order", 0),
                is_favorite=item.get("is_favorite", False),
            )
            for item in data
        ]

    # ── Comments ───────────────────────────────────────────────────────────

    def get_comments(self, task_id: str) -> list[Comment]:
        """Get comments for a task."""
        data = self._get_all("/comments", {"task_id": task_id})
        return [
            Comment(
                id=c["id"],
                task_id=c.get("task_id"),
                project_id=c.get("project_id"),
                content=c["content"],
                posted_at=c["posted_at"],
            )
            for c in data
        ]

    def create_comment(self, task_id: str, content: str) -> Comment:
        """Add a comment to a task."""
        data = self._request("POST", "/comments", json={"task_id": task_id, "content": content})
        return Comment(
            id=data["id"],
            task_id=data.get("task_id"),
            project_id=data.get("project_id"),
            content=data["content"],
            posted_at=data["posted_at"],
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
