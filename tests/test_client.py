"""TodoistClient against a mocked v1 API."""

import json
from typing import Any

import httpx
import pytest
import respx

from todoist_cli.client import TodoistClient, TodoistError


def test_pagination_follows_next_cursor(
    api: respx.MockRouter, client: TodoistClient, v1_task: Any
) -> None:
    route = api.get("/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"results": [v1_task(id="a")], "next_cursor": "c2"}),
            httpx.Response(200, json={"results": [v1_task(id="b")], "next_cursor": None}),
        ]
    )
    tasks = client.get_tasks()
    assert [t.id for t in tasks] == ["a", "b"]
    assert route.calls[1].request.url.params["cursor"] == "c2"


def test_filter_uses_filter_endpoint(
    api: respx.MockRouter, client: TodoistClient, v1_task: Any
) -> None:
    route = api.get("/tasks/filter").mock(
        return_value=httpx.Response(200, json={"results": [v1_task()], "next_cursor": None})
    )
    client.get_tasks(filter="today | overdue")
    assert route.calls[0].request.url.params["query"] == "today | overdue"


def test_task_field_mapping(api: respx.MockRouter, client: TodoistClient, v1_task: Any) -> None:
    data = v1_task(
        deadline={"date": "2026-10-12", "lang": "en"},
        checked=True,
        due={"date": "2026-10-07", "string": "today", "is_recurring": False},
    )
    api.get("/tasks/t1").mock(return_value=httpx.Response(200, json=data))
    task = client.get_task("t1")
    assert task.is_completed is True
    assert task.comment_count == 2
    assert task.order == 3
    assert task.created_at == "2026-10-01T10:00:00Z"
    assert task.deadline == "2026-10-12"
    assert task.due is not None and task.due.string == "today"


def test_get_sections_passes_project_id(
    api: respx.MockRouter, client: TodoistClient, v1_section: Any
) -> None:
    route = api.get("/sections").mock(
        return_value=httpx.Response(200, json={"results": [v1_section], "next_cursor": None})
    )
    sections = client.get_sections("p1")
    assert route.calls[0].request.url.params["project_id"] == "p1"
    assert sections[0].order == 2 and sections[0].name == "Sakshi"


def _sent(route: respx.Route) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(route.calls[0].request.content)
    return body


def test_update_task_deadline_only_when_given(
    api: respx.MockRouter, client: TodoistClient, v1_task: Any
) -> None:
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    client.update_task("t1", priority=4)
    assert "deadline_date" not in _sent(route)


def test_update_task_deadline_set_and_clear(
    api: respx.MockRouter, client: TodoistClient, v1_task: Any
) -> None:
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    client.update_task("t1", deadline_date="2026-10-12")
    client.update_task("t1", deadline_date=None)
    assert json.loads(route.calls[0].request.content) == {"deadline_date": "2026-10-12"}
    assert json.loads(route.calls[1].request.content) == {"deadline_date": None}


def test_create_task_section(api: respx.MockRouter, client: TodoistClient, v1_task: Any) -> None:
    route = api.post("/tasks").mock(return_value=httpx.Response(200, json=v1_task()))
    client.create_task("x", section_id="s1")
    assert _sent(route) == {"content": "x", "section_id": "s1"}


def test_http_error_raises_todoist_error(api: respx.MockRouter, client: TodoistClient) -> None:
    api.get("/tasks/zzz").mock(return_value=httpx.Response(404, text="nope"))
    with pytest.raises(TodoistError) as exc:
        client.get_task("zzz")
    assert exc.value.status_code == 404


def test_projects_labels_comments(
    api: respx.MockRouter, client: TodoistClient, v1_project: Any, v1_label: Any
) -> None:
    page = {"next_cursor": None}
    api.get("/projects").mock(
        return_value=httpx.Response(200, json={"results": [v1_project], **page})
    )
    api.get("/labels").mock(return_value=httpx.Response(200, json={"results": [v1_label], **page}))
    comment = {"id": "c1", "task_id": "t1", "content": "hi", "posted_at": "2026-10-01T00:00:00Z"}
    api.get("/comments").mock(return_value=httpx.Response(200, json={"results": [comment], **page}))
    api.post("/comments").mock(return_value=httpx.Response(200, json=comment))
    assert client.get_projects()[0].order == 1
    assert client.get_labels()[0].name == "quick"
    assert client.get_comments("t1")[0].content == "hi"
    assert client.create_comment("t1", "hi").id == "c1"


def test_close_reopen_delete(api: respx.MockRouter, client: TodoistClient) -> None:
    api.post("/tasks/t1/close").mock(return_value=httpx.Response(204))
    api.post("/tasks/t1/reopen").mock(return_value=httpx.Response(204))
    api.delete("/tasks/t1").mock(return_value=httpx.Response(204))
    client.close_task("t1")
    client.reopen_task("t1")
    client.delete_task("t1")


def test_network_error_wrapped(api: respx.MockRouter, client: TodoistClient) -> None:
    api.get("/tasks/t1").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(TodoistError):
        client.get_task("t1")
