# Todoist CLI (`t`)

A fast, shortcut-driven command-line interface for Todoist. Designed for power users who want quick task management without leaving the terminal.

## Features

- **Session-based numbering**: Tasks get simple numbers (1, 2, 3...) for quick reference
- **Custom shortcuts**: Define single-character shortcuts for labels and projects
- **Rich colored output**: Priority highlighting, overdue warnings, project colors
- **Bulk operations**: Complete, move, or tag multiple tasks at once
- **Natural language dates**: "tomorrow", "next monday", "every day"
- **Subtask support**: Full hierarchy display and creation
- **Today board**: `t` shows `today | overdue | p3` grouped by priority (P1 = the one focus task)
- **Sections and deadlines**: list/add into a project section, set hard deadlines

Targets the Todoist **API v1** (`https://api.todoist.com/api/v1`); the old REST v2 is retired.

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

Token lookup order: `TODOIST_API_TOKEN` env var, then `~/.config/todoist/config.json`
(key `"token"`, shared with other Todoist tooling), then `api-token` in `config.yml`.
A token from the env var or the shared file is never written back to `config.yml`.

**Option 1: Environment Variable**

```bash
export TODOIST_API_TOKEN="your_api_token_here"
```

Add this to your `~/.bashrc`, `~/.zshrc`, or shell profile to persist.

**Option 2: Config File**

Create `config.yml` in the project directory:

```yaml
api-token: your_api_token_here
```

**Option 3: Shared token file**

```json
{"token": "your_api_token_here"}
```

saved as `~/.config/todoist/config.json`.

### Shortcuts (Optional)

Create or edit `config.yml` to define shortcuts:

```yaml
shortcuts:
  labels:
    q: quick       # <= 10 minutes
    w: waiting
  projects:
    i: Inbox
    r: 🔬 Research
    t: 🎓 Teaching
    c: 🤝 Collabs
    s: 🏛 Service
    l: 🧰 Lab
    p: 🏠 Personal
    f: 💡 Someday
    u: 👥 Students
  priorities:
    u: p1          # 'u' expands to p1 (the focus task)
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
# Today board: today | overdue | p3, grouped by priority
t

# Make task #2 the one P1 focus task for today
t focus 2

# Mark tasks #3 and #4 as quick wins (@quick, due today)
t quick 3,4

# Add a task
t add "Fix bug @q p3 tomorrow"

# Complete tasks
t done 1 2 3
t done 1-3,5
```

## Commands Reference

### Today Board

```bash
t              # same as `t today` (alias `t tb`)
```

Groups the filter `today | overdue | p3` as `🔴 P1 Focus`, `🟠 P2`, `🔵 P3 Optional`, `⚪ P4`.
Session numbers run continuously from P1 downwards. Priority is inverted in the API
(API 4 = P1); the CLI always shows and accepts P1-P4.

```bash
t focus 2          # priority P1 + due today (range forms work: 1,3-5)
t quick 3,4        # adds @quick (keeps other labels) + due today
```

Recurring tasks keep their schedule: `focus` and `quick` do not reset their due date.

### Listing Tasks

```bash
# Default: today + overdue
t list

# List all tasks
t list --all
t list -a

# Filter by project
t list -p Research
t list -p r          # using shortcut

# Filter by section of a project (case-insensitive substring)
t ls -p u -S sakshi

# Filter by label
t list -l waiting
t list -l w          # using shortcut

# Use Todoist filter syntax
t list -f "today & @waiting"
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
t add "Review code" -p r
t add "Call mom" -p Personal

# An unknown -p project is an error (no silent Inbox fallback)
# Into a section of the project (-p or inline #project required)
t add "Reply about Ultima" -p u -S sakshi

# With labels (inline)
t add "Debug issue @quick @waiting"
t add "Quick email @q"      # shortcut for @quick

# With priority (p1=urgent/red, p4=low/default)
t add "Critical fix p1"
t add "Nice to have p4"

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
| `@label` | Add label | `@quick`, `@waiting` |
| `p1`-`p4` | Set priority | `p1` (urgent/focus), `p4` (normal) |
| Natural language | Due date | `tomorrow`, `next week`, `jan 15` |

Shortcuts are expanded automatically:
- `@q` → `@quick`, `@w` → `@waiting`
- `#r` → `#🔬 Research`, `#u` → `#👥 Students` (and the rest of your project shortcuts)

### Completing Tasks

```bash
# Complete single task
t done 1

# Complete multiple tasks
t done 1 2 3
t done 1-3,5

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

t edit 1 --labels "quick"
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
t move 1 Research

# Using shortcuts
t move 1 r

# Move multiple tasks
t move 1,2,3 Research
t move 1-5 Personal    # range syntax

# Shortcut
t mv 1 r
```

### Tagging Tasks

```bash
# Add label to task
t tag 1 waiting
t tag 1 @quick

# Using shortcuts
t tag 1 w              # adds @waiting

# Tag multiple tasks
t tag 1,2,3 waiting
t tag 1-5 quick         # range syntax
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

### Deadlines

A deadline is separate from the due date and shows as `⏰Mon DD` (red once past).

```bash
t deadline 1 2026-10-12     # set (ranges work: 1,3-5)
t deadline 1 none           # clear
```

### Sections

```bash
t sections u        # sections of a project, as `project / section` (alias: t sec)
t sections          # all sections, grouped by project
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
# Delete with one confirmation listing every task
t delete 1
t rm 1-3,5

# Force delete (no confirmation)
t delete 1 --force
t rm 1-3 -f
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
| `t today` | `t tb` (or bare `t`) |
| `t sections` | `t sec` |

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
- Reset when you run a new `t list` / `t today` command

**Workflow example:**
```bash
t                  # Today board, see numbers
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
t add "Email client about proposal @q p2 tomorrow" -p c
t add "Review draft @w p3 today" -p r
t add "Buy birthday gift @q" -p p
```

### Weekly Planning

```bash
# See all tasks
t list -a

# Move tasks to this week's focus
t move 5,8,12 r

# Tag batch
t tag 1-5 q

# Set due dates
t due 1 "monday"
t due 2 "tuesday"
t due 3 "wednesday"
```

### Project Focus

```bash
# List only research tasks
t list -p r

# Or with tree view for subtasks
t list -p r --tree
```

## Configuration File Reference

Full `config.yml` structure:

```yaml
# API token (optional if using TODOIST_API_TOKEN environment variable)
# api-token: your_token_here

# Optional: Define shortcuts for faster input
shortcuts:
  labels:
    q: quick
    w: waiting
  projects:
    i: Inbox
    r: 🔬 Research
    t: 🎓 Teaching
    c: 🤝 Collabs
    s: 🏛 Service
    l: 🧰 Lab
    p: 🏠 Personal
    f: 💡 Someday
    u: 👥 Students
  priorities:
    u: p1

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
