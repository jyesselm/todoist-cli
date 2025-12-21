"""Shortcut expansion for quick input."""

import re

from todoist_cli.models import ShortcutConfig, Project, Label


def _strip_emoji(text: str) -> str:
    """Strip leading emoji and whitespace from text."""
    return re.sub(r'^[\U0001F300-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF\s]+', '', text)


class ShortcutExpander:
    """Expands user-defined shortcuts in task content.

    Shortcuts are single-character or short codes defined in config:
    - @w -> @work (label shortcut)
    - #i -> #Inbox (project shortcut)
    - p1, p2, p3, p4 are kept as-is (native Todoist priority)
    """

    def __init__(
        self,
        shortcuts: ShortcutConfig,
        projects: list[Project] | None = None,
        labels: list[Label] | None = None,
    ):
        self._shortcuts = shortcuts
        self._projects = {p.name.lower(): p.name for p in (projects or [])}
        # Also store stripped versions (no emoji) for matching
        self._projects_stripped = {
            _strip_emoji(p.name).lower(): p.name for p in (projects or [])
        }
        self._labels = {l.name.lower(): l.name for l in (labels or [])}

        # Build reverse lookup: shortcut -> full name
        self._label_shortcuts = shortcuts.labels.copy()
        self._project_shortcuts = shortcuts.projects.copy()
        self._priority_shortcuts = shortcuts.priorities.copy()

    def expand(self, text: str) -> str:
        """Expand all shortcuts in text.

        Processes:
        1. Label shortcuts: @w -> @work
        2. Project shortcuts: #i -> #Inbox
        3. Priority shortcuts: u -> p1 (if defined)

        Native Todoist syntax (p1-p4, full @label, #project) is preserved.
        """
        result = text

        # Expand label shortcuts (@X where X is a shortcut)
        result = re.sub(
            r"@([\w/]+)",
            lambda m: self._expand_label_match(m),
            result,
        )

        # Expand project shortcuts (#X where X is a shortcut)
        result = re.sub(
            r"#([\w\U0001F300-\U0001F9FF]+)",
            lambda m: self._expand_project_match(m),
            result,
        )

        # Expand standalone priority shortcuts (not p1-p4)
        for shortcut, priority in self._priority_shortcuts.items():
            # Match word boundary to avoid partial matches
            pattern = rf"\b{re.escape(shortcut)}\b"
            result = re.sub(pattern, priority, result, flags=re.IGNORECASE)

        return result

    def _expand_label_match(self, match: re.Match) -> str:
        """Expand a label match."""
        label = match.group(1)
        expanded = self.expand_label(label)
        return f"@{expanded}" if expanded else match.group(0)

    def _expand_project_match(self, match: re.Match) -> str:
        """Expand a project match."""
        project = match.group(1)
        expanded = self.expand_project(project)
        return f"#{expanded}" if expanded else match.group(0)

    def expand_label(self, shortcut: str) -> str | None:
        """Expand a label shortcut.

        Returns expanded label name, or None if no match.
        Checks shortcuts first, then exact label names.
        """
        lower = shortcut.lower()

        # Check shortcuts first
        if lower in self._label_shortcuts:
            return self._label_shortcuts[lower]

        # Check if it's already a valid label name
        if lower in self._labels:
            return self._labels[lower]

        # Return original if no match (might be valid in Todoist)
        return shortcut

    def expand_project(self, shortcut: str) -> str | None:
        """Expand a project shortcut.

        Returns expanded project name, or None if no match.
        Supports nested projects and emoji names: 'work' matches '🔵 Work'.
        """
        lower = shortcut.lower()
        stripped = _strip_emoji(lower)

        # Check shortcuts first
        if lower in self._project_shortcuts:
            return self._project_shortcuts[lower]

        # Check if it's already a valid project name (exact match)
        if lower in self._projects:
            return self._projects[lower]

        # Check stripped version (without emoji)
        if stripped in self._projects_stripped:
            return self._projects_stripped[stripped]

        # Check for partial match with nested projects (e.g., "work" -> "Work/Projects")
        # Look for projects that start with the input followed by "/"
        prefix = stripped + "/"
        for project_stripped, project_name in self._projects_stripped.items():
            if project_stripped.startswith(prefix) or project_stripped == stripped:
                return project_name

        # Return original if no match
        return shortcut

    def expand_priority(self, shortcut: str) -> str | None:
        """Expand a priority shortcut.

        Returns p1-p4 string, or None if no match.
        """
        lower = shortcut.lower()

        if lower in self._priority_shortcuts:
            return self._priority_shortcuts[lower]

        # Check if already a valid priority
        if lower in ("p1", "p2", "p3", "p4"):
            return lower

        return None

    def list_shortcuts(self) -> dict[str, dict[str, str]]:
        """Get all defined shortcuts for display."""
        return {
            "labels": self._label_shortcuts.copy(),
            "projects": self._project_shortcuts.copy(),
            "priorities": self._priority_shortcuts.copy(),
        }
