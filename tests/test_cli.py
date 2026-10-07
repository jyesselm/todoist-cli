"""CLI commands via CliRunner against a mocked v1 API."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import yaml
from rich.console import Console
from typer.testing import CliRunner

from todoist_cli import cli, session
from todoist_cli.client import TodoistClient
from todoist_cli.config import ConfigManager
from todoist_cli.formatter import TaskFormatter
from todoist_cli.models import Label, Project, Task
from todoist_cli.session import SessionCache

runner = CliRunner()
PAGE = {"next_cursor": None}


@pytest.fixture(autouse=True)
def cli_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fresh module globals and a tmp session file for every test."""
    monkeypatch.setattr(session, "SESSION_FILE", tmp_path / "session.json")
    cfg = tmp_path / "config.yml"
    cfg.write_text(yaml.dump({"api-token": "x", "shortcuts": {"projects": {"u": "👥 Students"}}}))
    monkeypatch.setattr(cli, "_session_cache", SessionCache())
    monkeypatch.setattr(cli, "_config_manager", ConfigManager(cfg))
    monkeypatch.setattr(cli, "_projects", [Project(id="p1", name="👥 Students")])
    monkeypatch.setattr(cli, "_labels", [Label(id="l1", name="quick")])
    monkeypatch.setattr(cli, "_formatter", None)
    monkeypatch.setattr(cli, "_expander", None)
    monkeypatch.setattr(cli, "_client", TodoistClient("x"))
    monkeypatch.setenv("COLUMNS", "200")
    yield


def _run(*args: str, input: str | None = None) -> Any:
    return runner.invoke(cli.app, list(args), input=input)


def _list(api: respx.MockRouter, *tasks: dict[str, Any], path: str = "/tasks") -> respx.Route:
    return api.get(path).mock(
        return_value=httpx.Response(200, json={"results": list(tasks), **PAGE})
    )


def _body(route: respx.Route, i: int = 0) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(route.calls[i].request.content)
    return body


def test_today_groups_and_numbers(api: respx.MockRouter, v1_task: Any) -> None:
    _list(
        api,
        v1_task(id="a", content="Low thing", priority=1),
        v1_task(id="b", content="Focus thing", priority=4),
        v1_task(id="c", content="Mid thing", priority=3),
        path="/tasks/filter",
    )
    result = _run("today")
    assert result.exit_code == 0
    out = result.output
    assert out.index("P1 Focus") < out.index("P2") < out.index("P4")
    assert "P3 Optional" not in out
    assert out.index("Focus thing") < out.index("Mid thing") < out.index("Low thing")
    assert cli._session_cache.get_session_num("b") == 1
    assert cli._session_cache.get_session_num("a") == 3


def test_bare_t_runs_today(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(content="Hello"), path="/tasks/filter")
    result = _run()
    assert "Hello" in result.output and "P4" in result.output


def test_today_empty(api: respx.MockRouter) -> None:
    _list(api, path="/tasks/filter")
    assert "No tasks found" in _run("today").output


def test_focus(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(), path="/tasks/filter")
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    result = _run("focus", "1")
    assert result.exit_code == 0
    assert _body(route) == {"priority": 4, "due_string": "today"}


def test_focus_recurring_keeps_schedule(api: respx.MockRouter, v1_task: Any) -> None:
    due = {"date": "2026-10-09", "string": "every fri", "is_recurring": True}
    _list(api, v1_task(due=due), path="/tasks/filter")
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    _run("focus", "1")
    assert _body(route) == {"priority": 4}


def test_quick_keeps_labels(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(labels=["waiting"]), path="/tasks/filter")
    api.get("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task(labels=["waiting"])))
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    _run("quick", "1")
    assert _body(route) == {"labels": ["quick", "waiting"], "due_string": "today"}


def _two_tasks(api: respx.MockRouter, v1_task: Any) -> None:
    _list(
        api,
        v1_task(id="a", content="First", due={"date": "2026-01-01", "string": "x"}),
        v1_task(id="b", content="Second", due={"date": "2026-01-02", "string": "x"}),
    )
    _run("ls", "-a")


def test_rm_range_force(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    a = api.delete("/tasks/a").mock(return_value=httpx.Response(204))
    b = api.delete("/tasks/b").mock(return_value=httpx.Response(204))
    result = _run("rm", "1-2", "-f")
    assert result.exit_code == 0
    assert a.called and b.called


def test_rm_declined_deletes_nothing(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    a = api.delete("/tasks/a").mock(return_value=httpx.Response(204))
    b = api.delete("/tasks/b").mock(return_value=httpx.Response(204))
    result = _run("rm", "1-2", input="n\n")
    assert "First" in result.output and "Second" in result.output
    assert not a.called and not b.called


def test_rm_unknown_number(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    assert _run("rm", "9", "-f").exit_code == 1


def test_done_accepts_list_and_range(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    a = api.post("/tasks/a/close").mock(return_value=httpx.Response(204))
    b = api.post("/tasks/b/close").mock(return_value=httpx.Response(204))
    assert _run("done", "1", "2").exit_code == 0
    assert _run("done", "1-2").exit_code == 0
    assert a.call_count == 2 and b.call_count == 2


def test_sections_for_project(api: respx.MockRouter, v1_section: Any) -> None:
    route = api.get("/sections").mock(
        return_value=httpx.Response(200, json={"results": [v1_section], **PAGE})
    )
    result = _run("sections", "u")
    assert "👥 Students / Sakshi" in result.output
    assert route.calls[0].request.url.params["project_id"] == "p1"


def test_sections_all_and_empty(api: respx.MockRouter) -> None:
    _list(api, path="/sections")
    assert "No sections found" in _run("sec").output


def test_ls_section(api: respx.MockRouter, v1_task: Any, v1_section: Any) -> None:
    _list(api, v1_section, path="/sections")
    route = api.get("/tasks").mock(
        return_value=httpx.Response(200, json={"results": [v1_task()], **PAGE})
    )
    result = _run("ls", "-p", "u", "-S", "sak")
    assert result.exit_code == 0 and "Write paper" in result.output
    params = route.calls[0].request.url.params
    assert params["section_id"] == "s1" and params["project_id"] == "p1"


def test_ls_section_errors(api: respx.MockRouter, v1_section: Any) -> None:
    assert _run("ls", "-S", "x").exit_code == 1
    _list(api, v1_section, path="/sections")
    assert "Section not found" in _run("ls", "-p", "u", "-S", "zzz").output
    assert "Project not found" in _run("ls", "-p", "nope").output


def test_add_with_section(api: respx.MockRouter, v1_task: Any, v1_section: Any) -> None:
    _list(api, v1_section, path="/sections")
    route = api.post("/tasks").mock(return_value=httpx.Response(200, json=v1_task()))
    result = _run("add", "Reply", "-p", "u", "-S", "sakshi")
    assert result.exit_code == 0
    assert _body(route)["section_id"] == "s1" and _body(route)["project_id"] == "p1"


def test_add_section_requires_project(api: respx.MockRouter) -> None:
    assert _run("add", "Reply", "-S", "sakshi").exit_code == 1


def test_deadline_set_and_clear(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(), path="/tasks/filter")
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    assert _run("deadline", "1", "2026-10-12").exit_code == 0
    assert _run("deadline", "1", "none").exit_code == 0
    assert _body(route, 0) == {"deadline_date": "2026-10-12"}
    assert _body(route, 1) == {"deadline_date": None}


def test_deadline_bad_date() -> None:
    assert _run("deadline", "1", "next week").exit_code == 1


def test_deadline_rendered(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(deadline={"date": "2099-10-12", "lang": "en"}), path="/tasks/filter")
    assert "⏰Oct 12" in _run("today").output


def test_pri_tag_move(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    api.get("/tasks/a").mock(return_value=httpx.Response(200, json=v1_task(id="a")))
    r = api.post("/tasks/a").mock(return_value=httpx.Response(200, json=v1_task()))
    assert _run("pri", "1", "p1").exit_code == 0
    assert _run("tag", "1", "w").exit_code == 0
    assert _run("mv", "1", "u").exit_code == 0
    assert _body(r, 0) == {"priority": 4}
    assert _body(r, 1) == {"labels": ["w"]}
    assert _body(r, 2) == {"project_id": "p1"}
    assert _run("pri", "1", "p9").exit_code == 1


def test_formatter_detail_view(v1_task: Any) -> None:
    task = Task(**{**v1_task(), "deadline": "2020-01-01"})
    console = Console(record=True, width=100)
    console.print(TaskFormatter(console, cli._projects, []).format_single_task(task, 1))
    assert "Deadline: ⏰Jan 01" in console.export_text()


def test_list_rows_in_session_order(api: respx.MockRouter, v1_task: Any) -> None:
    _list(
        api,
        v1_task(id="b", content="Second", priority=4, due={"date": "2026-01-02", "string": "x"}),
        v1_task(id="a", content="First", priority=4, due={"date": "2026-01-01", "string": "x"}),
        path="/tasks/filter",
    )
    out = _run("today").output
    assert out.index("First") < out.index("Second")
    assert cli._session_cache.get_session_num("a") == 1


def _stale_session(tmp_path: Path) -> None:
    cli._session_cache._num_to_id = {1: "a"}
    cli._session_cache._id_to_num = {"a": 1}


def test_done_unloadable_task(api: respx.MockRouter, tmp_path: Path) -> None:
    _stale_session(tmp_path)
    api.get("/tasks/a").mock(return_value=httpx.Response(404, text="gone"))
    close = api.post("/tasks/a/close").mock(return_value=httpx.Response(204))
    result = _run("done", "1")
    assert result.exit_code == 1
    assert "could not be loaded" in result.output
    assert not close.called


@pytest.mark.parametrize("arg", ["a", "5-1", "-1", "1-3-5"])
def test_garbage_numbers_fail(api: respx.MockRouter, v1_task: Any, arg: str) -> None:
    _two_tasks(api, v1_task)
    result = _run("done", "--", arg)
    assert result.exit_code == 1
    assert "Invalid task numbers" in result.output


def test_out_of_range_numbers_fail(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    assert _run("done", "7").exit_code == 1


def test_empty_results_invalidate_numbers(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(id="a"), path="/tasks/filter")
    _run("today")
    _list(api, path="/tasks/filter")
    assert "No tasks found" in _run("today").output
    close = api.post("/tasks/a/close").mock(return_value=httpx.Response(204))
    assert _run("done", "1").exit_code == 1
    assert not close.called


def test_empty_ls_invalidates_numbers(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    _list(api)
    assert "No tasks found" in _run("ls", "-a").output
    assert _run("done", "1").exit_code == 1


def test_rm_multiple_args(api: respx.MockRouter, v1_task: Any) -> None:
    _two_tasks(api, v1_task)
    a = api.delete("/tasks/a").mock(return_value=httpx.Response(204))
    b = api.delete("/tasks/b").mock(return_value=httpx.Response(204))
    assert _run("rm", "1", "2", "-f").exit_code == 0
    assert a.called and b.called


def test_section_ambiguous_and_empty(api: respx.MockRouter, v1_section: Any) -> None:
    other = {**v1_section, "id": "s2", "name": "Sakshi B"}
    _list(api, {**v1_section, "name": "Sakshi A"}, other, path="/sections")
    result = _run("ls", "-p", "u", "-S", "sak")
    assert result.exit_code == 1
    assert "Sakshi A" in result.output and "Sakshi B" in result.output
    assert _run("ls", "-p", "u", "-S", "").exit_code == 1


def test_section_exact_beats_ambiguity(
    api: respx.MockRouter, v1_task: Any, v1_section: Any
) -> None:
    other = {**v1_section, "id": "s2", "name": "Sakshi B"}
    _list(api, v1_section, other, path="/sections")
    route = api.get("/tasks").mock(
        return_value=httpx.Response(200, json={"results": [v1_task()], **PAGE})
    )
    assert _run("ls", "-p", "u", "-S", "sakshi").exit_code == 0
    assert route.calls[0].request.url.params["section_id"] == "s1"


def test_focus_recurring_message(api: respx.MockRouter, v1_task: Any) -> None:
    due = {"date": "2026-10-09", "string": "every fri", "is_recurring": True}
    _list(api, v1_task(due=due), path="/tasks/filter")
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    result = _run("focus", "1")
    assert _body(route) == {"priority": 4}
    assert "recurring, date unchanged" in result.output


def test_tag_uses_fresh_labels(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(labels=["stale"]), path="/tasks/filter")
    api.get("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task(labels=["fresh"])))
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    _run("tag", "1", "w")
    assert _body(route) == {"labels": ["fresh", "w"]}


def test_ls_nested_and_label(api: respx.MockRouter, v1_task: Any) -> None:
    cli._projects.append(Project(id="p2", name="Child", parent_id="p1"))
    route = _list(
        api,
        v1_task(id="a", content="InChild", project_id="p2"),
        v1_task(id="b", content="Elsewhere", project_id="p9"),
    )
    out = _run("ls", "-p", "u", "-n").output
    assert "InChild" in out and "Elsewhere" not in out
    assert _run("ls", "-l", "quick").exit_code == 0
    assert route.calls[1].request.url.params["label"] == "quick"


def test_deadline_not_duplicated_in_detail(v1_task: Any) -> None:
    due = {"date": "2099-01-01", "string": "Jan 1"}
    task = Task(**{**v1_task(), "due": due, "deadline": "2099-10-12"})
    console = Console(record=True, width=100)
    console.print(TaskFormatter(console, cli._projects, []).format_single_task(task, 1))
    assert console.export_text().count("Oct 12") == 1


def test_deadline_without_due_has_no_dash(v1_task: Any) -> None:
    task = Task(**{**v1_task(), "deadline": "2099-10-12"})
    text = TaskFormatter(Console(), [], [])._format_due(task)
    assert text.plain == "⏰Oct 12"


def test_tag_refetch_failure_skips_task(api: respx.MockRouter, v1_task: Any) -> None:
    _list(api, v1_task(labels=["x"]), path="/tasks/filter")
    api.get("/tasks/t1").mock(return_value=httpx.Response(404, json={"error": "gone"}))
    route = api.post("/tasks/t1").mock(return_value=httpx.Response(200, json=v1_task()))
    _run("today")
    result = _run("tag", "1", "q")
    assert "could not be reloaded" in result.output
    assert route.call_count == 0
