"""Todoist CLI - Main command interface."""

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from todoist_cli.client import TodoistClient, TodoistError
from todoist_cli.config import ConfigManager
from todoist_cli.formatter import TaskFormatter
from todoist_cli.models import Label, Project, Section, Task
from todoist_cli.parser import TaskParser
from todoist_cli.session import SessionCache
from todoist_cli.shortcuts import ShortcutExpander, strip_emoji

TODAY_FILTER = "today | overdue | p3"

app = typer.Typer(
    name="t",
    help="Fast, shortcut-driven CLI for Todoist",
    no_args_is_help=False,
    invoke_without_command=True,
)

console = Console()

# Global state for session
_session_cache = SessionCache()
_config_manager: ConfigManager | None = None
_client: TodoistClient | None = None
_formatter: TaskFormatter | None = None
_expander: ShortcutExpander | None = None
_projects: list[Project] = []
_labels: list[Label] = []


def get_config() -> ConfigManager:
    """Get or create config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_client() -> TodoistClient:
    """Get or create API client."""
    global _client
    if _client is None:
        config = get_config()
        _client = TodoistClient(config.get_api_token())
    return _client


def get_projects_and_labels() -> tuple[list[Project], list[Label]]:
    """Get projects and labels (from cache or API)."""
    global _projects, _labels

    if _projects and _labels:
        return _projects, _labels

    config = get_config()
    cached_projects = config.get_cached_projects()
    cached_labels = config.get_cached_labels()

    if cached_projects and cached_labels:
        _projects = cached_projects
        _labels = cached_labels
    else:
        # Fetch from API
        client = get_client()
        _projects = client.get_projects()
        _labels = client.get_labels()
        # Update cache
        config.update_cached_data(_projects, _labels)

    return _projects, _labels


def get_formatter() -> TaskFormatter:
    """Get or create formatter."""
    global _formatter
    if _formatter is None:
        projects, labels = get_projects_and_labels()
        _formatter = TaskFormatter(console, projects, labels)
    return _formatter


def get_expander() -> ShortcutExpander:
    """Get or create shortcut expander."""
    global _expander
    if _expander is None:
        config = get_config()
        projects, labels = get_projects_and_labels()
        _expander = ShortcutExpander(config.get_shortcuts(), projects, labels)
    return _expander


def get_project_lookup() -> dict[str, str]:
    """Get project name -> ID mapping."""
    projects, _ = get_projects_and_labels()
    return {p.name: p.id for p in projects}


def _build_project_paths() -> dict[str, tuple[str, str]]:
    """Build full project paths using parent_id relationships.

    Returns:
        Dict mapping project_id -> (full_path, stripped_path)
        where stripped_path has emojis removed for matching
    """
    projects, _ = get_projects_and_labels()
    id_to_project = {p.id: p for p in projects}

    paths: dict[str, tuple[str, str]] = {}

    for project in projects:
        # Build path by walking up parent chain
        path_parts = [project.name]
        current = project
        while current.parent_id and current.parent_id in id_to_project:
            parent = id_to_project[current.parent_id]
            path_parts.insert(0, parent.name)
            current = parent

        full_path = "/".join(path_parts)
        # Create stripped version for matching (no emoji)
        stripped_parts = [strip_emoji(p) for p in path_parts]
        stripped_path = "/".join(stripped_parts)

        paths[project.id] = (full_path, stripped_path)

    return paths


def find_nested_project_ids(project_id: str) -> list[str]:
    """Find all nested (child) project IDs for a given project.

    Returns list of project IDs including the parent and all descendants.
    """
    projects, _ = get_projects_and_labels()

    # Build parent -> children mapping
    children_map: dict[str, list[str]] = {}
    for p in projects:
        if p.parent_id:
            if p.parent_id not in children_map:
                children_map[p.parent_id] = []
            children_map[p.parent_id].append(p.id)

    # BFS to find all descendants
    result = [project_id]
    queue = [project_id]
    while queue:
        current = queue.pop(0)
        if current in children_map:
            for child_id in children_map[current]:
                result.append(child_id)
                queue.append(child_id)

    return result


def find_project_id(project_name: str, project_lookup: dict[str, str]) -> str | None:
    """Find project ID by name, supporting nested projects and emoji names.

    Matches (case-insensitive):
    1. Exact match on project name (with or without emoji)
    2. Match on any ancestor in the path (e.g., 'work' matches '🔵 Work/Projects')
    3. Partial path match (e.g., 'work/proj' matches 'Work/Projects')
    """
    lower = project_name.lower()
    stripped_search = strip_emoji(lower)

    # Build project paths with hierarchy
    project_paths = _build_project_paths()

    # First: exact match on the project's own name (ignoring emoji)
    projects, _ = get_projects_and_labels()
    for project in projects:
        if strip_emoji(project.name).lower() == stripped_search:
            return project.id

    # Second: match if search term matches start of any path component
    for project_id, (full_path, stripped_path) in project_paths.items():
        path_lower = stripped_path.lower()
        # Check if search matches the start of the path
        if path_lower.startswith(stripped_search + "/") or path_lower == stripped_search:
            return project_id
        # Check if search matches any path component
        path_parts = path_lower.split("/")
        for part in path_parts:
            if part == stripped_search or part.startswith(stripped_search):
                return project_id

    return None


def get_task_by_num(num: int) -> tuple[str | None, Task | None]:
    """Get task ID and Task object by session number.

    Fetches from API if not in cache.

    Returns:
        Tuple of (task_id, task) - both None if not found
    """
    task_id = _session_cache.get_task_id(num)
    if not task_id:
        return None, None

    task = _session_cache.get_task(num)
    if not task:
        try:
            task = get_client().get_task(task_id)
        except TodoistError:
            return task_id, None

    return task_id, task


def _iter_tasks(nums: str) -> Iterator[tuple[int, str, Task]]:
    """Yield (num, task_id, task) for each valid session number in a range string.

    Exits with an error on unparseable input, or if no task ends up being processed.
    """
    formatter = get_formatter()
    parsed = _session_cache.parse_range(nums)
    if not parsed:
        formatter.format_error(f"Invalid task numbers: {nums!r}")
        raise typer.Exit(1)
    valid, invalid = _session_cache.validate_nums(parsed)
    if invalid:
        formatter.format_warning(f"Invalid task numbers: {invalid}")
    count = 0
    for num in valid:
        task_id, task = get_task_by_num(num)
        if not task_id or not task:
            formatter.format_warning(f"Task #{num} could not be loaded")
            continue
        count += 1
        yield num, task_id, task
    if count == 0:
        formatter.format_error("No tasks processed. Run 't list' first.")
        raise typer.Exit(1)


def _fresh_labels(task_id: str, num: int) -> list[str] | None:
    """Re-read a task's labels so a rewrite never clobbers changes made elsewhere."""
    try:
        return get_client().get_task(task_id).labels
    except TodoistError:
        get_formatter().format_warning(f"Task #{num} could not be reloaded; skipped")
        return None


def _resolve_project(project: str) -> tuple[str, str]:
    """Resolve a project shortcut/name to (display name, id), exiting if not found."""
    name = get_expander().expand_project(project.lstrip("#")) or project
    project_id = find_project_id(name, get_project_lookup())
    if not project_id:
        get_formatter().format_error(f"Project not found: {project}")
        raise typer.Exit(1)
    return name, project_id


def _resolve_section(project_id: str, section: str) -> str:
    """Find a section id in a project (exact name, else a unique substring), or exit."""
    formatter = get_formatter()
    needle = section.strip().lower()
    if not needle:
        formatter.format_error("Section name is empty")
        raise typer.Exit(1)
    sections: list[Section] = get_client().get_sections(project_id)
    exact = [s for s in sections if s.name.lower() == needle]
    found = exact or [s for s in sections if needle in s.name.lower()]
    if not found:
        formatter.format_error(f"Section not found: {section}")
        raise typer.Exit(1)
    if len(found) > 1:
        names = ", ".join(s.name for s in found)
        formatter.format_error(f"Section '{section}' is ambiguous: {names}")
        raise typer.Exit(1)
    return found[0].id


def _is_recurring(task: Task) -> bool:
    """Whether the task repeats (moving its due date would destroy the recurrence)."""
    return bool(task.due and task.due.is_recurring)


def _due_today(task: Task) -> dict[str, Any]:
    """Params that move a task to today; recurring tasks keep their schedule."""
    return {} if _is_recurring(task) else {"due_string": "today"}


def _recurring_note(task: Task) -> str:
    """Suffix for success lines when a recurring task's date was left alone."""
    return " (recurring, date unchanged)" if _is_recurring(task) else ""


# ── Default Command ────────────────────────────────────────────────────────


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Show the Today board (today | overdue | p3, grouped by priority)."""
    if ctx.invoked_subcommand is None:
        today_board()


# ── Today Board ────────────────────────────────────────────────────────────


@app.command("today")
@app.command("tb")
def today_board() -> None:
    """Show the Today board grouped by priority (P1 focus first)."""
    try:
        tasks = get_client().get_tasks(filter=TODAY_FILTER)
        if not tasks:
            _session_cache.build_from_tasks([])
            console.print("[dim]No tasks found[/dim]")
            raise typer.Exit(0)
        _session_cache.build_from_tasks(tasks, by_priority=True)
        console.print(get_formatter().format_by_priority(tasks, _session_cache))
        console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")
    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


# ── List Tasks ─────────────────────────────────────────────────────────────


def _project_tasks(project: str, nested: bool, section: str | None) -> list[Task]:
    """Tasks of a project, optionally restricted to a section or including children."""
    client = get_client()
    _, project_id = _resolve_project(project)
    if section is not None:
        section_id = _resolve_section(project_id, section)
        return client.get_tasks(project_id=project_id, section_id=section_id)
    if nested:
        # Fetch all tasks once and filter locally (much faster than one call per project)
        ids = set(find_nested_project_ids(project_id))
        return [t for t in client.get_tasks() if t.project_id in ids]
    return client.get_tasks(project_id=project_id)


@app.command("list")
@app.command("ls")
def list_tasks(
    filter: Annotated[
        str,
        typer.Option("-f", "--filter", help="Todoist filter query"),
    ] = "today | overdue",
    project: Annotated[
        str | None,
        typer.Option("-p", "--project", help="Filter by project"),
    ] = None,
    nested: Annotated[
        bool,
        typer.Option("-n", "--nested", help="Include nested/child projects"),
    ] = False,
    label: Annotated[
        str | None,
        typer.Option("-l", "--label", help="Filter by label"),
    ] = None,
    untagged: Annotated[
        bool,
        typer.Option("-u", "--untagged", help="Show only tasks without any labels"),
    ] = False,
    search: Annotated[
        str | None,
        typer.Option("-s", "--search", help="Text search in task content"),
    ] = None,
    tree: Annotated[
        bool,
        typer.Option("--tree", "-t", help="Show as tree with subtasks"),
    ] = False,
    all_tasks: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all tasks (no filter)"),
    ] = False,
    section: Annotated[
        str | None,
        typer.Option("-S", "--section", help="Section of the -p project (name substring)"),
    ] = None,
) -> None:
    """List tasks with optional filtering."""
    try:
        formatter = get_formatter()
        client = get_client()
        if section is not None and not project:
            formatter.format_error("--section requires -p/--project")
            raise typer.Exit(1)
        if all_tasks:
            tasks = client.get_tasks()
        elif project:
            tasks = _project_tasks(project, nested, section)
        elif label:
            tasks = client.get_tasks(label=get_expander().expand_label(label))
        else:
            tasks = client.get_tasks(filter=filter)

        # Apply text search filter
        if search:
            search_lower = search.lower()
            tasks = [t for t in tasks if search_lower in t.content.lower()]

        # Filter to only untagged tasks
        if untagged:
            tasks = [t for t in tasks if not t.labels]

        if not tasks:
            _session_cache.build_from_tasks([])
            console.print("[dim]No tasks found[/dim]")
            raise typer.Exit(0)

        # Build session cache
        _session_cache.build_from_tasks(tasks)

        # Display
        if tree:
            console.print(formatter.format_task_tree(tasks, _session_cache))
        else:
            console.print(formatter.format_task_list(tasks, _session_cache))
        console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


# ── Add Task ───────────────────────────────────────────────────────────────


@app.command("add")
@app.command("a")
def add_task(
    content: Annotated[str, typer.Argument(help="Task content with inline syntax")],
    parent: Annotated[
        int | None,
        typer.Option("-P", "--parent", help="Parent task session number"),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option("-p", "--project", help="Project (name or shortcut)"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("-d", "--description", help="Task description"),
    ] = None,
    section: Annotated[
        str | None,
        typer.Option("-S", "--section", help="Section of the project (name substring)"),
    ] = None,
) -> None:
    """Add a new task.

    Supports inline syntax:
    - @label for labels (or shortcuts like @q for @quick)
    - p1-p4 for priority
    - Natural language dates: "tomorrow", "next monday", etc.

    Use -p for projects with spaces/emoji: t add "task" -p s

    Examples:
        t add "Reply to Swati @q tomorrow" -p s
        t add "Fix bug" -p l
        t add "Subtask" --parent 1
        t add "Reply to Sakshi" -p u -S sakshi
    """
    try:
        client = get_client()
        formatter = get_formatter()
        expander = get_expander()
        parser = TaskParser()

        # Expand shortcuts in content (labels, priorities)
        expanded = expander.expand(content)

        # Parse content
        parsed = parser.parse(expanded)

        # Build API params
        params = parser.build_api_params(parsed, get_project_lookup())

        # Handle project option (takes precedence over inline #project)
        if project:
            params["project_id"] = _resolve_project(project)[1]

        # Handle section (needs a project, from -p or inline #project)
        if section is not None:
            if "project_id" not in params:
                formatter.format_error("--section requires -p or an inline #project")
                raise typer.Exit(1)
            params["section_id"] = _resolve_section(params["project_id"], section)

        # Handle parent task
        if parent:
            parent_id = _session_cache.get_task_id(parent)
            if parent_id:
                params["parent_id"] = parent_id
            else:
                formatter.format_warning(f"Parent #{parent} not found. Creating as top-level task.")

        # Add description
        if description:
            params["description"] = description

        # Create task
        task = client.create_task(**params)

        # Get project name for display
        project_display = ""
        if task.project_id:
            projects, _ = get_projects_and_labels()
            for p in projects:
                if p.id == task.project_id:
                    project_display = p.name
                    break

        formatter.format_success(f"Created: {task.content}")
        if project_display and project_display != "Inbox":
            console.print(f"  [dim]Project: {project_display}[/dim]")
        if task.due:
            console.print(f"  [dim]Due: {task.due.string}[/dim]")
        if task.labels:
            console.print(f"  [dim]Labels: {', '.join(task.labels)}[/dim]")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Complete Tasks ─────────────────────────────────────────────────────────


@app.command("done")
@app.command("d")
def complete_tasks(
    nums: Annotated[
        list[str],
        typer.Argument(help="Session numbers or ranges to complete"),
    ],
) -> None:
    """Complete one or more tasks by session number.

    Examples:
        t done 1
        t done 1 2 3
        t done 1-3,5
    """
    try:
        client = get_client()
        for _, task_id, task in _iter_tasks(",".join(nums)):
            client.close_task(task_id)
            get_formatter().format_success(f"Completed: {task.content}")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


# ── Focus / Quick / Deadline ───────────────────────────────────────────────


@app.command("focus")
def focus_tasks(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1' or '1,3-5')")],
) -> None:
    """Make tasks today's P1 focus (priority P1 + due today).

    Example:
        t focus 2
    """
    try:
        client = get_client()
        for _, task_id, task in _iter_tasks(nums):
            client.update_task(task_id, priority=4, **_due_today(task))
            get_formatter().format_success(f"Focus: {task.content}{_recurring_note(task)}")
    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


@app.command("quick")
def quick_tasks(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1' or '1,3-5')")],
) -> None:
    """Mark tasks as quick wins (@quick label + due today).

    Example:
        t quick 3,4
    """
    try:
        client = get_client()
        for num, task_id, task in _iter_tasks(nums):
            current = _fresh_labels(task_id, num)
            if current is None:
                continue
            client.update_task(task_id, labels=sorted({*current, "quick"}), **_due_today(task))
            get_formatter().format_success(f"Quick: {task.content}{_recurring_note(task)}")
    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


@app.command("deadline")
def set_deadline(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1' or '1,3-5')")],
    date: Annotated[str, typer.Argument(help="YYYY-MM-DD, or 'none' to clear")],
) -> None:
    """Set (or clear) the hard deadline on tasks.

    Examples:
        t deadline 1 2026-10-12
        t deadline 1-3 none
    """
    value: str | None = None
    if date.lower() != "none":
        try:
            value = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            get_formatter().format_error("DATE must be YYYY-MM-DD or 'none'")
            raise typer.Exit(1) from None
    try:
        client = get_client()
        for _, task_id, task in _iter_tasks(nums):
            client.update_task(task_id, deadline_date=value)
            what = f"deadline {value}" if value else "no deadline"
            get_formatter().format_success(f"Set {what}: {task.content}")
    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


# ── Edit Task ──────────────────────────────────────────────────────────────


@app.command("edit")
@app.command("e")
def edit_task(
    num: Annotated[int, typer.Argument(help="Task session number")],
    content: Annotated[
        str | None,
        typer.Option("-c", "--content", help="New task content"),
    ] = None,
    priority: Annotated[
        int | None,
        typer.Option("-p", "--priority", help="Priority (1-4, 1=urgent)"),
    ] = None,
    due: Annotated[
        str | None,
        typer.Option("-d", "--due", help="Due date (natural language)"),
    ] = None,
    labels: Annotated[
        str | None,
        typer.Option("-l", "--labels", help="Labels (comma-separated)"),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("-i", "--interactive", help="Interactive editing mode"),
    ] = False,
) -> None:
    """Edit a task.

    Examples:
        t edit 1 -c "Updated content"
        t edit 1 -p 4 -d "tomorrow"
        t edit 1 --interactive
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id = _session_cache.get_task_id(num)

        if not task_id:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        # Get task from cache or API
        task = _session_cache.get_task(num)
        if not task:
            task = client.get_task(task_id)

        if interactive:
            # Interactive mode
            console.print(f"\n[bold]Editing:[/bold] {task.content}\n")

            content = Prompt.ask("Content", default=task.content)
            priority = IntPrompt.ask(
                "Priority (1-4, 1=urgent)",
                default=task.priority,
            )
            due_str = task.due.string if task.due else ""
            due = Prompt.ask("Due date", default=due_str) or None
            labels_str = ",".join(task.labels)
            labels_input = Prompt.ask("Labels (comma-sep)", default=labels_str)
            labels_list = (
                [x.strip() for x in labels_input.split(",") if x.strip()] if labels_input else None
            )

            updated = client.update_task(
                task_id,
                content=content,
                priority=priority,
                due_string=due,
                labels=labels_list,
            )
        else:
            # Flag-based editing
            update_params: dict[str, Any] = {}
            if content:
                update_params["content"] = content
            if priority:
                update_params["priority"] = priority
            if due:
                update_params["due_string"] = due
            if labels:
                update_params["labels"] = [x.strip() for x in labels.split(",")]

            if not update_params:
                formatter.format_error("No changes specified. Use flags or --interactive")
                raise typer.Exit(1)

            updated = client.update_task(task_id, **update_params)

        formatter.format_success(f"Updated: {updated.content}")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Move Tasks ─────────────────────────────────────────────────────────────


@app.command("move")
@app.command("mv")
def move_tasks(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1,2,3' or '1-5')")],
    project: Annotated[str, typer.Argument(help="Target project (name or shortcut)")],
) -> None:
    """Move tasks to a different project.

    Examples:
        t move 1 Inbox
        t move 1-5 #Work
        t move 1,2,3 i
    """
    try:
        client = get_client()
        project_name, project_id = _resolve_project(project)

        for _, task_id, task in _iter_tasks(nums):
            client.update_task(task_id, project_id=project_id)
            get_formatter().format_success(f"Moved '{task.content}' to {project_name}")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Tag Tasks ──────────────────────────────────────────────────────────────


@app.command("tag")
def tag_tasks(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1,2,3' or '1-5')")],
    label: Annotated[str, typer.Argument(help="Label to add (name or shortcut)")],
) -> None:
    """Add a label to tasks.

    Examples:
        t tag 1 urgent
        t tag 1-5 @waiting
        t tag 1,2,3 q
    """
    try:
        client = get_client()
        label_name = get_expander().expand_label(label.lstrip("@")) or label

        for num, task_id, task in _iter_tasks(nums):
            current = _fresh_labels(task_id, num)
            if current is None:
                continue
            client.update_task(task_id, labels=sorted({*current, label_name}))
            get_formatter().format_success(f"Tagged '{task.content}' with @{label_name}")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Priority Command ───────────────────────────────────────────────────────


@app.command("priority")
@app.command("pri")
def set_priority(
    nums: Annotated[str, typer.Argument(help="Task numbers (e.g., '1,2,3' or '1-5')")],
    priority: Annotated[str, typer.Argument(help="Priority: p1/p2/p3/p4 or 1/2/3/4 (1=urgent)")],
) -> None:
    """Set priority on tasks.

    Priority levels (Todoist convention):
    - p1 / 1 = Urgent (red)
    - p2 / 2 = High (orange)
    - p3 / 3 = Medium (blue)
    - p4 / 4 = Low (default, no color)

    Examples:
        t pri 1 p1          # Set task 1 to urgent (red)
        t pri 1-5 1         # Set tasks 1-5 to urgent
        t priority 1,2,3 p3 # Set multiple to medium
    """
    try:
        client = get_client()
        formatter = get_formatter()

        # Parse priority (accept p1-p4 or just 1-4)
        # User-facing: p1=urgent, p4=low
        # API values:  4=urgent,  1=low (inverted!)
        pri_str = priority.lower().lstrip("p")
        try:
            user_pri = int(pri_str)
            if user_pri < 1 or user_pri > 4:
                raise ValueError()
        except ValueError:
            formatter.format_error("Priority must be p1-p4 or 1-4")
            raise typer.Exit(1) from None

        # Convert user-facing priority to API value (invert: p1->4, p2->3, p3->2, p4->1)
        api_pri = 5 - user_pri

        # Set priority on each task
        pri_names = {1: "urgent", 2: "high", 3: "medium", 4: "low"}
        for _, task_id, task in _iter_tasks(nums):
            client.update_task(task_id, priority=api_pri)
            formatter.format_success(f"Set '{task.content}' to {pri_names[user_pri]} (p{user_pri})")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Reschedule Commands ────────────────────────────────────────────────────


@app.command("bump")
def bump_task(
    num: Annotated[int, typer.Argument(help="Task session number")],
) -> None:
    """Move task to tomorrow.

    Example:
        t bump 1
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, task = get_task_by_num(num)

        if not task_id:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        client.update_task(task_id, due_string="tomorrow")
        content = task.content if task else f"Task {task_id}"
        formatter.format_success(f"Bumped '{content}' to tomorrow")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


@app.command("defer")
def defer_task(
    num: Annotated[int, typer.Argument(help="Task session number")],
    offset: Annotated[str, typer.Argument(help="Time offset (e.g., '+3d', '+1w')")],
) -> None:
    """Defer task by a time offset.

    Supports:
    - +Nd: Add N days
    - +Nw: Add N weeks

    Examples:
        t defer 1 +3d
        t defer 1 +1w
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, task = get_task_by_num(num)

        if not task_id:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        # Parse offset
        offset = offset.lstrip("+")
        if offset.endswith("d"):
            days = int(offset[:-1])
        elif offset.endswith("w"):
            days = int(offset[:-1]) * 7
        else:
            formatter.format_error("Invalid offset. Use +Nd (days) or +Nw (weeks)")
            raise typer.Exit(1)

        # Calculate new date
        if task and task.due:
            try:
                current = datetime.strptime(task.due.date, "%Y-%m-%d")
            except ValueError:
                current = datetime.now()
        else:
            current = datetime.now()

        new_date = current + timedelta(days=days)
        new_date_str = new_date.strftime("%Y-%m-%d")

        client.update_task(task_id, due_date=new_date_str)
        content = task.content if task else f"Task {task_id}"
        formatter.format_success(f"Deferred '{content}' to {new_date.strftime('%b %d')}")

    except (ValueError, TodoistError) as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


@app.command("due")
def set_due(
    num: Annotated[int, typer.Argument(help="Task session number")],
    date: Annotated[str, typer.Argument(help="Due date (natural language)")],
) -> None:
    """Set task due date.

    Examples:
        t due 1 "next monday"
        t due 1 "every day"
        t due 1 "jan 15"
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, _ = get_task_by_num(num)

        if not task_id:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        updated = client.update_task(task_id, due_string=date)
        if updated.due:
            formatter.format_success(f"Set due: {updated.due.string}")
        else:
            formatter.format_success("Cleared due date")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Comments ───────────────────────────────────────────────────────────────


@app.command("comments")
def show_comments(
    num: Annotated[int, typer.Argument(help="Task session number")],
) -> None:
    """View comments on a task.

    Example:
        t comments 1
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, task = get_task_by_num(num)

        if not task_id or not task:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        comments = client.get_comments(task_id)

        panel = formatter.format_single_task(task, num, comments)
        console.print(panel)

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


@app.command("comment")
def add_comment(
    num: Annotated[int, typer.Argument(help="Task session number")],
    text: Annotated[str, typer.Argument(help="Comment text")],
) -> None:
    """Add a comment to a task.

    Example:
        t comment 1 "Waiting for review"
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, task = get_task_by_num(num)

        if not task_id:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        client.create_comment(task_id, text)
        content = task.content if task else f"Task {task_id}"
        formatter.format_success(f"Added comment to '{content}'")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Projects / Labels ──────────────────────────────────────────────────────


@app.command("projects")
@app.command("proj")
def list_projects(
    flat: Annotated[
        bool,
        typer.Option("--flat", "-f", help="Show flat list instead of tree"),
    ] = False,
) -> None:
    """List all projects.

    Shows projects in a tree structure by default.

    Examples:
        t projects          # Show project tree
        t proj -f           # Show flat list
    """
    projects, _ = get_projects_and_labels()

    if not projects:
        console.print("[dim]No projects found[/dim]")
        raise typer.Exit(0)

    if flat:
        # Flat list with full paths
        project_paths = _build_project_paths()
        for project in sorted(projects, key=lambda p: project_paths.get(p.id, ("", ""))[1].lower()):
            full_path, _ = project_paths.get(project.id, (project.name, project.name))
            console.print(f"  {full_path}")
    else:
        # Tree structure
        # Find root projects (no parent)
        roots = [p for p in projects if not p.parent_id]

        # Build children map
        children_map: dict[str, list[Project]] = {}
        for p in projects:
            if p.parent_id:
                if p.parent_id not in children_map:
                    children_map[p.parent_id] = []
                children_map[p.parent_id].append(p)

        # Sort children by order
        for pid in children_map:
            children_map[pid].sort(key=lambda p: p.order)

        def print_tree(project: Project, prefix: str = "", is_last: bool = True) -> None:
            connector = "└── " if is_last else "├── "
            console.print(f"{prefix}{connector}{project.name}")
            children = children_map.get(project.id, [])
            for i, child in enumerate(children):
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(child, next_prefix, i == len(children) - 1)

        # Print each root
        roots.sort(key=lambda p: p.order)
        for i, root in enumerate(roots):
            print_tree(root, "", i == len(roots) - 1)

    console.print(f"\n[dim]{len(projects)} project(s)[/dim]")


@app.command("labels")
def list_labels() -> None:
    """List all labels.

    Example:
        t labels
    """
    _, labels = get_projects_and_labels()

    if not labels:
        console.print("[dim]No labels found[/dim]")
        raise typer.Exit(0)

    for label in sorted(labels, key=lambda lb: lb.name.lower()):
        console.print(f"  @{label.name}")

    console.print(f"\n[dim]{len(labels)} label(s)[/dim]")


@app.command("sections")
@app.command("sec")
def list_sections(
    project: Annotated[
        str | None,
        typer.Argument(help="Project (name or shortcut); omit for all projects"),
    ] = None,
) -> None:
    """List sections as `project / section`.

    Examples:
        t sections u
        t sec
    """
    try:
        projects, _ = get_projects_and_labels()
        project_id = _resolve_project(project)[1] if project else None
        sections = get_client().get_sections(project_id)
        rank = {p.id: (p.order, p.name) for p in projects}
        names = {p.id: p.name for p in projects}
        sections.sort(key=lambda s: (rank.get(s.project_id, (0, "")), s.order))
        for sec in sections:
            console.print(f"  {names.get(sec.project_id, sec.project_id)} / {sec.name}")
        if not sections:
            console.print("[dim]No sections found[/dim]")
    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


# ── Sync / Config ──────────────────────────────────────────────────────────


@app.command("sync")
def sync_config() -> None:
    """Sync labels and projects from Todoist.

    Fetches current labels and projects and updates local cache.
    Also displays shortcut mapping status.
    """
    try:
        global _projects, _labels

        client = get_client()
        config = get_config()
        formatter = get_formatter()

        console.print("[dim]Fetching from Todoist...[/dim]")

        _projects = client.get_projects()
        _labels = client.get_labels()

        config.update_cached_data(_projects, _labels)

        formatter.format_success(f"Synced {len(_projects)} projects, {len(_labels)} labels")

        # Show current shortcuts
        shortcuts = config.get_shortcuts()
        if shortcuts.labels or shortcuts.projects:
            console.print("\n[bold]Current shortcuts:[/bold]")
            if shortcuts.labels:
                console.print("  [cyan]Labels:[/cyan]")
                for short, full in shortcuts.labels.items():
                    console.print(f"    {short} → @{full}")
            if shortcuts.projects:
                console.print("  [cyan]Projects:[/cyan]")
                for short, full in shortcuts.projects.items():
                    console.print(f"    {short} → #{full}")
        else:
            console.print(
                "\n[dim]No shortcuts defined. Add them to config.yml:[/dim]\n"
                "  shortcuts:\n"
                "    labels:\n"
                "      q: quick\n"
                "    projects:\n"
                "      i: Inbox"
            )

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


@app.command("config")
def show_config() -> None:
    """Show current configuration."""
    config = get_config()

    console.print(f"[bold]Config file:[/bold] {config.config_path}")

    shortcuts = config.get_shortcuts()
    console.print("\n[bold]Shortcuts:[/bold]")

    if shortcuts.labels:
        console.print("  [cyan]Labels:[/cyan]")
        for short, full in shortcuts.labels.items():
            console.print(f"    {short} → @{full}")
    else:
        console.print("  [dim]No label shortcuts[/dim]")

    if shortcuts.projects:
        console.print("  [cyan]Projects:[/cyan]")
        for short, full in shortcuts.projects.items():
            console.print(f"    {short} → #{full}")
    else:
        console.print("  [dim]No project shortcuts[/dim]")

    if shortcuts.priorities:
        console.print("  [cyan]Priorities:[/cyan]")
        for short, full in shortcuts.priorities.items():
            console.print(f"    {short} → {full}")


# ── View Task ──────────────────────────────────────────────────────────────


@app.command("view")
@app.command("v")
def view_task(
    num: Annotated[int, typer.Argument(help="Task session number")],
) -> None:
    """View task details.

    Example:
        t view 1
    """
    try:
        client = get_client()
        formatter = get_formatter()

        task_id, task = get_task_by_num(num)

        if not task_id or not task:
            formatter.format_error(f"Task #{num} not found. Run 't list' first.")
            raise typer.Exit(1)

        # Always fetch: v1 note_count lags behind comments added via the API
        comments = client.get_comments(task_id)

        panel = formatter.format_single_task(task, num, comments)
        console.print(panel)

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1)


# ── Delete Task ────────────────────────────────────────────────────────────


@app.command("delete")
@app.command("rm")
def delete_task(
    nums: Annotated[list[str], typer.Argument(help="Task numbers (e.g., '1 2' or '1-3,5')")],
    force: Annotated[
        bool,
        typer.Option("-f", "--force", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete tasks (one confirmation listing all of them).

    Example:
        t delete 1
        t rm 1-3 -f
    """
    try:
        client = get_client()
        items = list(_iter_tasks(",".join(nums)))

        if not force:
            listing = "\n".join(f"  - {task.content}" for _, _, task in items)
            if not Confirm.ask(f"Delete {len(items)} task(s)?\n{listing}\n"):
                console.print("[dim]Cancelled[/dim]")
                raise typer.Exit(0)

        for _, task_id, task in items:
            client.delete_task(task_id)
            get_formatter().format_success(f"Deleted: {task.content}")

    except TodoistError as e:
        get_formatter().format_error(str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
