"""TaskParser extraction and API param building."""

from todoist_cli.parser import TaskParser


def test_extracts_labels_project_priority_due() -> None:
    parsed = TaskParser().parse("Review draft @quick @waiting #Inbox p1 tomorrow")
    assert parsed.content == "Review draft"
    assert parsed.labels == ["quick", "waiting"]
    assert parsed.project == "Inbox"
    assert parsed.priority == 1
    assert parsed.due_string == "tomorrow"


def test_highest_priority_wins_and_inverts() -> None:
    parser = TaskParser()
    parsed = parser.parse("x p4 p2")
    assert parsed.priority == 4
    assert parser.build_api_params(parser.parse("x p1"))["priority"] == 4
    assert parser.build_api_params(parser.parse("x p4"))["priority"] == 1


def test_no_extras() -> None:
    parser = TaskParser()
    parsed = parser.parse("plain task")
    assert parser.build_api_params(parsed) == {"content": "plain task"}


def test_project_lookup_ignores_emoji() -> None:
    parser = TaskParser()
    params = parser.build_api_params(parser.parse("x #teaching"), {"🎓 Teaching": "p9"})
    assert params["project_id"] == "p9"


def test_project_lookup_nested_prefix() -> None:
    parser = TaskParser()
    params = parser.build_api_params(parser.parse("x #lab"), {"🧰 Lab/Orders": "p7"})
    assert params["project_id"] == "p7"


def test_unknown_project_leaves_no_id() -> None:
    parser = TaskParser()
    assert "project_id" not in parser.build_api_params(parser.parse("x #nope"), {"Inbox": "p1"})
