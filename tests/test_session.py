"""SessionCache numbering, ranges, and persistence."""

from datetime import date, timedelta
from pathlib import Path

import pytest

from todoist_cli import session
from todoist_cli.models import DueDate, Task
from todoist_cli.session import SessionCache


@pytest.fixture(autouse=True)
def tmp_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "session.json"
    monkeypatch.setattr(session, "SESSION_FILE", path)
    return path


def _task(id: str, offset: int | None, priority: int = 1) -> Task:
    due = None
    if offset is not None:
        day = (date.today() + timedelta(days=offset)).isoformat()
        due = DueDate(date=day, string=day)
    return Task(id=id, content=id, project_id="p", priority=priority, due=due)


def test_parse_range() -> None:
    cache = SessionCache()
    cache.build_from_tasks([_task(str(i), 0) for i in range(10)])
    assert cache.parse_range("1") == [1]
    assert cache.parse_range("1,3-5, 8") == [1, 3, 4, 5, 8]
    assert cache.parse_range("x,2,a-b") == [2]


@pytest.mark.parametrize("text", ["a", "5-1", "1 2", "-1", "1-3-5", ""])
def test_parse_range_garbage(text: str) -> None:
    cache = SessionCache()
    cache.build_from_tasks([_task("a", 0)])
    assert cache.parse_range(text) == []


def test_parse_range_clamped_to_max() -> None:
    cache = SessionCache()
    cache.build_from_tasks([_task("a", 0), _task("b", 1)])
    assert cache.parse_range("1-30000000") == [1, 2, 30000000]
    assert cache.validate_nums(cache.parse_range("1-30000000")) == ([1, 2], [30000000])


def test_sort_order_and_priority() -> None:
    cache = SessionCache()
    tasks = [
        _task("none", None),
        _task("future", 3),
        _task("today_low", 0, 1),
        _task("today_high", 0, 4),
        _task("overdue", -2),
    ]
    mapping = cache.build_from_tasks(tasks)
    assert [mapping[i] for i in range(1, 6)] == [
        "overdue",
        "today_high",
        "today_low",
        "future",
        "none",
    ]


def test_by_priority_numbering() -> None:
    cache = SessionCache()
    mapping = cache.build_from_tasks([_task("a", -1, 1), _task("b", 3, 4)], by_priority=True)
    assert mapping == {1: "b", 2: "a"}


def test_validate_and_accessors() -> None:
    cache = SessionCache()
    cache.build_from_tasks([_task("a", 0), _task("b", 1)])
    assert cache.validate_nums([1, 2, 9]) == ([1, 2], [9])
    assert cache.get_task_ids([2, 9]) == ["b"]
    assert cache.get_task(1) is not None
    assert cache.get_session_num("b") == 2
    assert (cache.count, cache.max_num) == (2, 2)


def test_file_round_trip(tmp_session: Path) -> None:
    SessionCache().build_from_tasks([_task("a", 0), _task("b", 1)])
    assert tmp_session.exists()
    loaded = SessionCache()
    assert loaded.get_task_id(2) == "b"
    assert loaded.get_task(2) is None  # tasks are not persisted


def test_expired_file_is_dropped(tmp_session: Path) -> None:
    import os

    SessionCache().build_from_tasks([_task("a", 0)])
    os.utime(tmp_session, (0, 0))
    assert SessionCache().get_task_id(1) is None
    assert not tmp_session.exists()


def test_corrupt_file_ignored(tmp_session: Path) -> None:
    tmp_session.write_text("{nope")
    assert SessionCache().count == 0
