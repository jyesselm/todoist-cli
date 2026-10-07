"""Rich-based task display formatting."""

from datetime import date, datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from todoist_cli.models import Comment, Label, Project, Task
from todoist_cli.session import SessionCache


class TaskFormatter:
    """Format tasks for Rich console output."""

    # Priority colors (API uses inverted values: api_priority=4 means P1/urgent)
    PRIORITY_STYLES = {
        4: Style(color="red", bold=True),  # API 4 = P1 - Urgent
        3: Style(color="orange1", bold=True),  # API 3 = P2 - High
        2: Style(color="yellow"),  # API 2 = P3 - Medium
        1: Style(color="white"),  # API 1 = P4 - Normal
    }

    PRIORITY_MARKERS = {
        4: "!!!",
        3: "!!",
        2: "!",
        1: "",
    }

    PRIORITY_HEADINGS = {
        4: "🔴 P1 Focus",
        3: "🟠 P2",
        2: "🔵 P3 Optional",
        1: "⚪ P4",
    }

    # Todoist color name to Rich color mapping
    COLOR_MAP = {
        "berry_red": "red",
        "red": "red",
        "orange": "orange1",
        "yellow": "yellow",
        "olive_green": "olive_drab1",
        "lime_green": "green",
        "green": "green",
        "mint_green": "spring_green1",
        "teal": "cyan",
        "sky_blue": "sky_blue1",
        "light_blue": "light_sky_blue1",
        "blue": "blue",
        "grape": "purple",
        "violet": "violet",
        "lavender": "plum1",
        "magenta": "magenta",
        "salmon": "light_coral",
        "charcoal": "grey70",
        "grey": "grey50",
        "taupe": "rosy_brown",
    }

    def __init__(
        self,
        console: Console,
        projects: list[Project] | None = None,
        labels: list[Label] | None = None,
    ):
        self._console = console
        self._projects = {p.id: p for p in (projects or [])}
        self._labels = {lb.name: lb for lb in (labels or [])}
        self._project_colors = {
            p.id: self.COLOR_MAP.get(p.color, "white") for p in (projects or [])
        }

    def format_task_list(
        self,
        tasks: list[Task],
        session_cache: SessionCache,
        show_project: bool = True,
    ) -> Table:
        """Format tasks as a Rich Table.

        Args:
            tasks: Tasks to display
            session_cache: Session number mapping
            show_project: Whether to show project column
        """
        table = Table(
            show_header=True,
            header_style="bold",
            border_style="dim",
            row_styles=["", "dim"],
        )

        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Task", min_width=30)
        table.add_column("Due", width=20, justify="right")
        if show_project:
            table.add_column("Project", width=15)
        table.add_column("Labels", width=20)

        ordered = sorted(tasks, key=lambda t: session_cache.get_session_num(t.id) or 0)
        for task in ordered:
            num = session_cache.get_session_num(task.id)
            if num is None:
                continue

            # Format each column
            num_text = Text(str(num), style="cyan bold")
            content_text = self._format_content(task)
            due_text = self._format_due(task)

            row = [num_text, content_text, due_text]

            if show_project:
                project_text = self._format_project(task)
                row.append(project_text)

            labels_text = self._format_labels(task)
            row.append(labels_text)

            table.add_row(*row)

        return table

    def format_by_priority(self, tasks: list[Task], session_cache: SessionCache) -> Group:
        """Format tasks as one table per priority (P1 first), skipping empty groups."""
        parts: list[Text | Table] = []
        for api_pri in sorted(self.PRIORITY_HEADINGS, reverse=True):
            group = [t for t in tasks if t.priority == api_pri]
            if group:
                parts.append(Text(f"\n{self.PRIORITY_HEADINGS[api_pri]}", style="bold"))
                parts.append(self.format_task_list(group, session_cache))
        return Group(*parts)

    def format_task_tree(
        self,
        tasks: list[Task],
        session_cache: SessionCache,
    ) -> Tree:
        """Format tasks with subtask hierarchy as Rich Tree.

        Args:
            tasks: Tasks to display (flat list, hierarchy built from parent_id)
            session_cache: Session number mapping
        """
        # Build parent -> children mapping
        children: dict[str | None, list[Task]] = {None: []}
        for task in tasks:
            parent = task.parent_id
            if parent not in children:
                children[parent] = []
            children[parent].append(task)

        tree = Tree("[bold]Tasks[/bold]")
        self._add_tree_children(tree, None, children, session_cache)

        return tree

    def _add_tree_children(
        self,
        parent_node: Tree,
        parent_id: str | None,
        children: dict[str | None, list[Task]],
        session_cache: SessionCache,
    ) -> None:
        """Recursively add children to tree."""
        for task in children.get(parent_id, []):
            num = session_cache.get_session_num(task.id)
            if num is None:
                continue

            # Format node label
            label = self._format_tree_node(task, num)
            node = parent_node.add(label)

            # Recurse for subtasks
            if task.id in children:
                self._add_tree_children(node, task.id, children, session_cache)

    def _format_tree_node(self, task: Task, num: int) -> Text:
        """Format a single tree node."""
        style = self.PRIORITY_STYLES.get(task.priority, Style())
        marker = self.PRIORITY_MARKERS.get(task.priority, "")

        text = Text()
        text.append(f"[{num}] ", style="cyan bold")

        if marker:
            text.append(f"{marker} ", style=style)

        text.append(task.content, style=style)

        # Add due date if present
        if task.due:
            due_text = self._format_due(task)
            text.append(" ")
            text.append(due_text)

        return text

    def _format_content(self, task: Task) -> Text:
        """Format task content with priority styling."""
        style = self.PRIORITY_STYLES.get(task.priority, Style())
        marker = self.PRIORITY_MARKERS.get(task.priority, "")

        text = Text()
        if marker:
            text.append(f"{marker} ", style=style)
        text.append(task.content, style=style)

        # Add comment indicator
        if task.comment_count > 0:
            text.append(f" 💬{task.comment_count}", style="dim")

        return text

    def _format_due(self, task: Task) -> Text:
        """Format due date with overdue highlighting, plus the deadline if set."""
        if not task.due and task.deadline:
            return Text(self._format_deadline(task.deadline).plain.strip(), style="dim")
        text = self._format_due_only(task)
        if task.deadline:
            text.append_text(self._format_deadline(task.deadline))
        return text

    def _format_deadline(self, deadline: str) -> Text:
        """Format a deadline as ` ⏰Mon DD` (red bold when past)."""
        try:
            day = datetime.strptime(deadline, "%Y-%m-%d").date()
        except ValueError:
            return Text(f" ⏰{deadline}", style="dim")
        style = "red bold" if day < date.today() else "dim"
        return Text(f" ⏰{day.strftime('%b %d')}", style=style)

    def _format_due_only(self, task: Task) -> Text:
        """Format the due date alone."""
        if not task.due:
            return Text("-", style="dim")

        today = date.today()
        try:
            due_date = datetime.strptime(task.due.date, "%Y-%m-%d").date()
        except ValueError:
            return Text(task.due.string, style="dim")

        # Determine style based on due date
        if due_date < today:
            style = "red bold"
            if (today - due_date).days == 1:
                display = "Yesterday"
            else:
                display = f"{(today - due_date).days}d overdue"
        elif due_date == today:
            style = "green bold"
            display = "Today"
        elif (due_date - today).days == 1:
            style = "yellow"
            display = "Tomorrow"
        elif (due_date - today).days <= 7:
            style = "blue"
            display = due_date.strftime("%A")  # Day name
        else:
            style = "dim"
            display = due_date.strftime("%b %d")

        # Add recurring indicator
        if task.due.is_recurring:
            display = f"🔄 {display}"

        return Text(display, style=style)

    def _format_project(self, task: Task) -> Text:
        """Format project name with color."""
        project = self._projects.get(task.project_id)
        if not project:
            return Text("-", style="dim")

        color = self._project_colors.get(task.project_id, "white")
        return Text(project.name, style=color)

    def _format_labels(self, task: Task) -> Text:
        """Format labels."""
        if not task.labels:
            return Text("-", style="dim")

        text = Text()
        for i, label_name in enumerate(task.labels):
            if i > 0:
                text.append(" ")

            label = self._labels.get(label_name)
            color = self.COLOR_MAP.get(label.color, "white") if label else "white"
            text.append(f"@{label_name}", style=color)

        return text

    def format_single_task(
        self,
        task: Task,
        session_num: int,
        comments: list[Comment] | None = None,
    ) -> Panel:
        """Format detailed view of a single task."""
        content = Text()

        # Header with number and content
        content.append(f"[{session_num}] ", style="cyan bold")
        style = self.PRIORITY_STYLES.get(task.priority, Style())
        content.append(task.content, style=style)
        content.append("\n\n")

        # Description
        if task.description:
            content.append(task.description, style="dim")
            content.append("\n\n")

        # Metadata
        content.append("Priority: ", style="bold")
        content.append(f"P{5 - task.priority}", style=style)
        content.append("\n")

        content.append("Due: ", style="bold")
        content.append(self._format_due_only(task))
        content.append("\n")

        if task.deadline:
            content.append("Deadline:", style="bold")
            content.append_text(self._format_deadline(task.deadline))
            content.append("\n")

        content.append("Project: ", style="bold")
        content.append(self._format_project(task))
        content.append("\n")

        if task.labels:
            content.append("Labels: ", style="bold")
            content.append(self._format_labels(task))
            content.append("\n")

        # Comments
        if comments:
            content.append("\n")
            content.append("Comments:\n", style="bold")
            for comment in comments:
                posted = comment.posted_at[:10]  # Just the date
                content.append(f"  [{posted}] ", style="dim")
                content.append(comment.content)
                content.append("\n")

        return Panel(content, title="Task Details", border_style="blue")

    def format_success(self, message: str) -> None:
        """Print success message."""
        self._console.print(f"[green]✓[/green] {message}")

    def format_error(self, message: str) -> None:
        """Print error message."""
        self._console.print(f"[red]✗[/red] {message}")

    def format_warning(self, message: str) -> None:
        """Print warning message."""
        self._console.print(f"[yellow]![/yellow] {message}")
