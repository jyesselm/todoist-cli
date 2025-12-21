"""Task content parser for Todoist syntax."""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedTask:
    """Result of parsing task content."""

    content: str  # Cleaned content without parsed elements
    labels: list[str] = field(default_factory=list)
    project: str | None = None
    priority: int | None = None
    due_string: str | None = None


class TaskParser:
    """Parse task content for Todoist syntax elements.

    Extracts:
    - Labels: @work, @home
    - Projects: #Inbox, #Work
    - Priority: p1, p2, p3, p4
    - Due dates: natural language at end of content

    The parsed content is cleaned to remove these elements,
    leaving only the task description.
    """

    # Patterns for extraction
    PRIORITY_PATTERN = re.compile(r"\bp([1-4])\b", re.IGNORECASE)
    LABEL_PATTERN = re.compile(r"@([\w/]+)")  # Allow slashes in labels
    PROJECT_PATTERN = re.compile(r"#([\w\U0001F300-\U0001F9FF]+)")  # Allow emoji in projects

    # Common date keywords that indicate start of due date
    DATE_KEYWORDS = [
        "today",
        "tomorrow",
        "yesterday",
        "next",
        "this",
        "every",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]

    def parse(self, content: str) -> ParsedTask:
        """Parse task content and extract Todoist syntax elements.

        Args:
            content: Raw task content with inline syntax

        Returns:
            ParsedTask with cleaned content and extracted elements
        """
        working = content.strip()
        labels: list[str] = []
        project: str | None = None
        priority: int | None = None
        due_string: str | None = None

        # Extract labels
        for match in self.LABEL_PATTERN.finditer(working):
            labels.append(match.group(1))
        working = self.LABEL_PATTERN.sub("", working)

        # Extract project (take first one if multiple)
        project_match = self.PROJECT_PATTERN.search(working)
        if project_match:
            project = project_match.group(1)
        working = self.PROJECT_PATTERN.sub("", working)

        # Extract priority (take highest if multiple)
        for match in self.PRIORITY_PATTERN.finditer(working):
            p = int(match.group(1))
            if priority is None or p > priority:
                priority = p
        working = self.PRIORITY_PATTERN.sub("", working)

        # Extract due date (look for date keywords)
        working, due_string = self._extract_due_date(working)

        # Clean up extra whitespace
        working = " ".join(working.split())

        return ParsedTask(
            content=working,
            labels=labels,
            project=project,
            priority=priority,
            due_string=due_string,
        )

    def _extract_due_date(self, content: str) -> tuple[str, str | None]:
        """Extract due date from content.

        Looks for date keywords and extracts everything from that point
        as the due date string.

        Returns:
            Tuple of (content without date, due string or None)
        """
        lower = content.lower()

        # Find the earliest date keyword
        earliest_pos = len(content)
        found_keyword = None

        for keyword in self.DATE_KEYWORDS:
            # Look for keyword as whole word
            pattern = rf"\b{keyword}\b"
            match = re.search(pattern, lower)
            if match and match.start() < earliest_pos:
                earliest_pos = match.start()
                found_keyword = keyword

        if found_keyword is None:
            return content, None

        # Extract everything from the keyword onwards as due string
        due_string = content[earliest_pos:].strip()
        cleaned_content = content[:earliest_pos].strip()

        return cleaned_content, due_string

    def build_api_params(
        self,
        parsed: ParsedTask,
        project_lookup: dict[str, str] | None = None,
    ) -> dict:
        """Convert parsed task to Todoist API parameters.

        Args:
            parsed: Parsed task data
            project_lookup: Optional mapping of project name -> ID

        Returns:
            Dict of API parameters for task creation
        """
        params: dict = {"content": parsed.content}

        if parsed.labels:
            params["labels"] = parsed.labels

        if parsed.priority:
            params["priority"] = parsed.priority

        if parsed.due_string:
            params["due_string"] = parsed.due_string

        if parsed.project and project_lookup:
            # Look up project ID by name (case-insensitive)
            for name, project_id in project_lookup.items():
                if name.lower() == parsed.project.lower():
                    params["project_id"] = project_id
                    break

        return params
