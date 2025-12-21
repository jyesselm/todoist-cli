"""Session-based task numbering for quick reference."""

import json
import tempfile
from datetime import date, datetime
from pathlib import Path

from todoist_cli.models import Task

# Session cache file (persists for 10 minutes)
SESSION_FILE = Path(tempfile.gettempdir()) / "todoist_cli_session.json"
SESSION_TTL_SECONDS = 600  # 10 minutes


class SessionCache:
    """Maps session numbers (1, 2, 3...) to task IDs.

    Numbers are assigned based on display order:
    1. Overdue tasks first (by date)
    2. Today's tasks (by priority, then creation time)
    3. Future tasks (by date)
    """

    def __init__(self):
        self._num_to_id: dict[int, str] = {}
        self._id_to_num: dict[str, int] = {}
        self._tasks: dict[str, Task] = {}
        self._load_from_file()

    def build_from_tasks(self, tasks: list[Task]) -> dict[int, str]:
        """Build session number mapping from task list.

        Args:
            tasks: List of tasks to number

        Returns:
            Mapping of session number to task ID
        """
        self._num_to_id.clear()
        self._id_to_num.clear()
        self._tasks.clear()

        # Sort tasks for consistent numbering
        sorted_tasks = self._sort_tasks(tasks)

        for i, task in enumerate(sorted_tasks, start=1):
            self._num_to_id[i] = task.id
            self._id_to_num[task.id] = i
            self._tasks[task.id] = task

        # Persist to temp file
        self._save_to_file()

        return self._num_to_id.copy()

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by due date, priority, then creation."""
        today = date.today()

        def sort_key(task: Task) -> tuple:
            # Parse due date
            if task.due:
                try:
                    due_date = datetime.strptime(task.due.date, "%Y-%m-%d").date()
                except ValueError:
                    due_date = date.max
            else:
                due_date = date.max

            # Determine category: 0=overdue, 1=today, 2=future, 3=no date
            if due_date < today:
                category = 0
            elif due_date == today:
                category = 1
            elif task.due:
                category = 2
            else:
                category = 3

            # Priority is inverted (4 is urgent in Todoist)
            priority = -task.priority

            return (category, due_date, priority, task.created_at)

        return sorted(tasks, key=sort_key)

    def get_task_id(self, session_num: int) -> str | None:
        """Get task ID for a session number."""
        return self._num_to_id.get(session_num)

    def get_task(self, session_num: int) -> Task | None:
        """Get task object for a session number."""
        task_id = self.get_task_id(session_num)
        return self._tasks.get(task_id) if task_id else None

    def get_session_num(self, task_id: str) -> int | None:
        """Get session number for a task ID."""
        return self._id_to_num.get(task_id)

    def get_task_ids(self, session_nums: list[int]) -> list[str]:
        """Get task IDs for multiple session numbers.

        Skips invalid session numbers.
        """
        return [
            self._num_to_id[n] for n in session_nums if n in self._num_to_id
        ]

    def parse_range(self, range_str: str) -> list[int]:
        """Parse a range string into session numbers.

        Supports:
        - Single numbers: "1" -> [1]
        - Comma-separated: "1,2,3" -> [1, 2, 3]
        - Ranges: "1-5" -> [1, 2, 3, 4, 5]
        - Mixed: "1,3-5,8" -> [1, 3, 4, 5, 8]
        """
        result = []

        for part in range_str.split(","):
            part = part.strip()
            if "-" in part:
                # Range: "1-5"
                try:
                    start, end = part.split("-", 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    result.extend(range(start_num, end_num + 1))
                except ValueError:
                    continue
            else:
                # Single number
                try:
                    result.append(int(part))
                except ValueError:
                    continue

        return sorted(set(result))

    def validate_nums(self, nums: list[int]) -> tuple[list[int], list[int]]:
        """Validate session numbers.

        Returns:
            Tuple of (valid_nums, invalid_nums)
        """
        valid = [n for n in nums if n in self._num_to_id]
        invalid = [n for n in nums if n not in self._num_to_id]
        return valid, invalid

    @property
    def count(self) -> int:
        """Number of tasks in cache."""
        return len(self._num_to_id)

    @property
    def max_num(self) -> int:
        """Highest session number, or 0 if empty."""
        return max(self._num_to_id.keys()) if self._num_to_id else 0

    def _load_from_file(self) -> None:
        """Load session cache from temp file if recent."""
        try:
            if not SESSION_FILE.exists():
                return

            # Check if file is still valid (within TTL)
            mtime = SESSION_FILE.stat().st_mtime
            age = datetime.now().timestamp() - mtime
            if age > SESSION_TTL_SECONDS:
                SESSION_FILE.unlink(missing_ok=True)
                return

            with open(SESSION_FILE) as f:
                data = json.load(f)

            self._num_to_id = {int(k): v for k, v in data.get("num_to_id", {}).items()}
            self._id_to_num = {v: int(k) for k, v in data.get("num_to_id", {}).items()}
            # Note: Tasks aren't persisted, only the ID mapping

        except (json.JSONDecodeError, OSError):
            # Ignore corrupt or inaccessible cache
            pass

    def _save_to_file(self) -> None:
        """Save session cache to temp file."""
        try:
            data = {
                "num_to_id": self._num_to_id,
                "saved_at": datetime.now().isoformat(),
            }
            with open(SESSION_FILE, "w") as f:
                json.dump(data, f)
        except OSError:
            # Ignore write errors
            pass
