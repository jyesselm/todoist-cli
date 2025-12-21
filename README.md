# Todoist CLI (`t`)

A fast, shortcut-driven command-line interface for Todoist. Designed for power users who want quick task management without leaving the terminal.

## Features

- **Session-based numbering**: Tasks get simple numbers (1, 2, 3...) for quick reference
- **Custom shortcuts**: Define single-character shortcuts for labels and projects
- **Rich colored output**: Priority highlighting, overdue warnings, project colors
- **Bulk operations**: Complete, move, or tag multiple tasks at once
- **Natural language dates**: "tomorrow", "next monday", "every day"
- **Subtask support**: Full hierarchy display and creation

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd todoist-cli

# Install in development mode
pip install -e .

# Verify installation
t --help
```

## Configuration

### API Token (Required)

Get your API token from: https://todoist.com/app/settings/integrations/developer

**Option 1: Environment Variable (Recommended)**

```bash
export TODOIST_API_TOKEN="your_api_token_here"
```

Add this to your `~/.bashrc`, `~/.zshrc`, or shell profile to persist.

**Option 2: Config File**

Create `config.yml` in the project directory:

```yaml
api-token: your_api_token_here
```

> **Note**: Environment variable takes precedence over config file.

### Shortcuts (Optional)

Create or edit `config.yml` to define shortcuts:

```yaml
shortcuts:
  labels:
    w: work
    h: home
    u: urgent
    c: context/computer
    e: context/email
  projects:
    i: Inbox
    w: Work
    p: Personal
  priorities:
    u: p4   # 'u' expands to p4 (urgent)
```

Copy from `config.example.yml` to get started:

```bash
cp config.example.yml config.yml
```

### Auto-discover Labels and Projects

Run `t sync` to fetch your existing labels and projects from Todoist. This populates the cache and shows you what shortcuts you can define:

```bash
t sync
```

## Quick Start

```bash
# View today's tasks and overdue items
t

# Add a task
t add "Review pull request"

# Add with labels, priority, and due date
t add "Fix bug @w p3 tomorrow"

# Complete task #1
t done 1

# Complete multiple tasks
t done 1 2 3
```

## Commands Reference

### Listing Tasks

```bash
# Default: today + overdue
t

# Same as above
t list

# List all tasks
t list --all
t list -a

# Filter by project
t list -p Work
t list -p w          # using shortcut

# Filter by label
t list -l urgent
t list -l u          # using shortcut

# Use Todoist filter syntax
t list -f "today & @work"
t list -f "p1 | p2"
t list -f "no date"

# Text search
t list -s "keyword"
t list -a -s "bug"   # search all tasks

# Show as tree (with subtasks)
t list --tree
t list -t
```

### Adding Tasks

```bash
# Basic task (goes to Inbox)
t add "Buy groceries"

# With project (use -p flag for projects with spaces/emoji)
t add "Review code" -p w
t add "Call mom" -p Personal

# With labels (inline)
t add "Debug issue @coding @urgent"
t add "Read paper @c"      # shortcut for @context/computer

# With priority (p1=normal, p4=urgent)
t add "Critical fix p4"
t add "Nice to have p1"

# With due date (natural language)
t add "Submit report tomorrow"
t add "Weekly review every monday"
t add "Meeting next friday at 2pm"

# With description
t add "Research topic" -d "Look into machine learning approaches"

# Create subtask (parent by session number)
t add "Subtask item" --parent 1
t add "Another subtask" -P 1
```

#### Inline Syntax

When adding tasks, you can use inline syntax:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `@label` | Add label | `@work`, `@urgent` |
| `p1`-`p4` | Set priority | `p4` (urgent), `p1` (normal) |
| Natural language | Due date | `tomorrow`, `next week`, `jan 15` |

Shortcuts are expanded automatically:
- `@w` → `@work` (if configured)
- `@c` → `@context/computer` (if configured)

### Completing Tasks

```bash
# Complete single task
t done 1

# Complete multiple tasks
t done 1 2 3

# Shortcut
t d 1
```

### Editing Tasks

```bash
# Edit with flags
t edit 1 --content "Updated task name"
t edit 1 -c "New name"

t edit 1 --priority 4
t edit 1 -p 3

t edit 1 --due "next monday"
t edit 1 -d "tomorrow"

t edit 1 --labels "work,urgent"
t edit 1 -l "coding"

# Combine multiple changes
t edit 1 -c "New name" -p 4 -d "today"

# Interactive mode (prompts for each field)
t edit 1 --interactive
t edit 1 -i
```

### Moving Tasks

```bash
# Move to project
t move 1 Inbox
t move 1 Work

# Using shortcuts
t move 1 w

# Move multiple tasks
t move 1,2,3 Work
t move 1-5 Personal    # range syntax

# Shortcut
t mv 1 w
```

### Tagging Tasks

```bash
# Add label to task
t tag 1 urgent
t tag 1 @work

# Using shortcuts
t tag 1 w              # adds @work

# Tag multiple tasks
t tag 1,2,3 urgent
t tag 1-5 coding       # range syntax
```

### Rescheduling Tasks

```bash
# Move to tomorrow
t bump 1

# Defer by offset
t defer 1 +1d          # add 1 day
t defer 1 +3d          # add 3 days
t defer 1 +1w          # add 1 week
t defer 1 +2w          # add 2 weeks

# Set specific due date
t due 1 "next monday"
t due 1 "jan 15"
t due 1 "every day"    # recurring
```

### Viewing Task Details

```bash
# View full task details
t view 1
t v 1

# View with comments
t comments 1
```

### Comments

```bash
# View comments on a task
t comments 1

# Add a comment
t comment 1 "This is blocked by API changes"
t comment 1 "Waiting for review"
```

### Deleting Tasks

```bash
# Delete with confirmation
t delete 1
t rm 1

# Force delete (no confirmation)
t delete 1 --force
t rm 1 -f
```

### Configuration Commands

```bash
# Sync labels and projects from Todoist
t sync

# Show current shortcuts
t config
```

## Shortcuts Reference

### Command Shortcuts

| Full Command | Shortcut |
|--------------|----------|
| `t list` | `t ls` |
| `t add` | `t a` |
| `t done` | `t d` |
| `t edit` | `t e` |
| `t move` | `t mv` |
| `t view` | `t v` |
| `t delete` | `t rm` |

### Range Syntax

For commands that accept multiple tasks:

| Syntax | Meaning |
|--------|---------|
| `1` | Single task |
| `1 2 3` | Multiple tasks (space-separated) |
| `1,2,3` | Multiple tasks (comma-separated) |
| `1-5` | Range (tasks 1 through 5) |
| `1,3-5,8` | Mixed |

## Session Numbers

Tasks are assigned session numbers (1, 2, 3...) when you list them. These numbers:

- Are based on display order (overdue first, then today, then future)
- Persist for 10 minutes between commands
- Reset when you run a new `t list` command

**Workflow example:**
```bash
t                  # List tasks, see numbers
t done 1           # Complete task #1 (works because numbers persist)
t bump 2           # Move task #2 to tomorrow
t                  # Refresh the list (numbers may change)
```

## Priority Levels

Todoist uses inverted priority numbers:

| Display | API Value | Color |
|---------|-----------|-------|
| P1 (urgent) | 4 | Red |
| P2 (high) | 3 | Orange |
| P3 (medium) | 2 | Yellow |
| P4 (normal) | 1 | White |

When adding/editing, use the display value: `p1`, `p2`, `p3`, `p4`

## Example Workflows

### Morning Review

```bash
# See what's due today
t

# Bump non-urgent items to tomorrow
t bump 3
t bump 5

# Complete quick wins
t done 1 2
```

### Adding Tasks from Brain Dump

```bash
t add "Email client about proposal @e p2 tomorrow" -p w
t add "Review PR #123 @co p3 today" -p w
t add "Buy birthday gift @h" -p p
t add "Read chapter 5 @r" -p p
```

### Weekly Planning

```bash
# See all tasks
t list -a

# Move tasks to this week's focus
t move 5,8,12 Work

# Tag batch for context
t tag 1-5 focus

# Set due dates
t due 1 "monday"
t due 2 "tuesday"
t due 3 "wednesday"
```

### Project Focus

```bash
# List only work tasks
t list -p w

# Or with tree view for subtasks
t list -p w --tree
```

## Configuration File Reference

Full `config.yml` structure:

```yaml
# API token (optional if using TODOIST_API_TOKEN environment variable)
# api-token: your_token_here

# Optional: Define shortcuts for faster input
shortcuts:
  # Label shortcuts: single char -> full label name
  labels:
    w: work
    h: home
    c: context/computer
    e: context/email
    r: context/reading
    l: context/lab
    tq: time/quick
    tl: time/long
    tw: time/waiting
    co: type/coding
    wr: type/writing
    an: type/analysis

  # Project shortcuts: single char -> full project name
  projects:
    i: Inbox
    w: Work
    p: Personal
    t: Teaching

  # Priority shortcuts (optional)
  priorities:
    u: p4    # 'u' becomes p4 (urgent)

# Auto-populated by 't sync' - don't edit manually
cached:
  projects: [...]
  labels: [...]
  last_sync: "2025-12-21T10:00:00"
```

## Troubleshooting

### "No API token found"

Either set the environment variable:
```bash
export TODOIST_API_TOKEN="your_api_token_here"
```

Or add to `config.yml`:
```yaml
api-token: your_token_here
```

### "Task #X not found"

Run `t` or `t list` first to populate session numbers, then run your command.

### Labels/projects not recognized

Run `t sync` to refresh the cache from Todoist.

### Shortcuts not working

Check `t config` to see your current shortcuts. Ensure they're defined in `config.yml`.

## Dependencies

- Python 3.11+
- typer (CLI framework)
- rich (colored output)
- httpx (HTTP client)
- pydantic (data validation)
- pyyaml (config parsing)

## License

MIT
