---
id: ref-todoist-cli-complete
title: Todoist CLI Complete Setup Guide
date: 2025-11-21
type: reference/tool
tags:
  - reference/tool
  - topic/tool/cli
  - topic/todoist
  - topic/productivity
  - project/active
status: published
summary: Complete Todoist CLI installation, configuration, color schemes, and advanced usage guide.
updated: 2025-11-21
---

# Todoist CLI Complete Setup Guide

## Installation Options

### Option 1: Python Package (todoist-python)
```bash
# Install via pip
pip install todoist-python

# Or with pip3
pip3 install todoist-python
```

### Option 2: Node.js CLI (@sachinraja/todoist-cli) - Recommended
```bash
# Using npm
npm install -g @sachinraja/todoist-cli

# Using yarn  
yarn global add @sachinraja/todoist-cli

# Using pnpm
pnpm add -g @sachinraja/todoist-cli
```

### Option 3: Go Implementation (sachaos/todoist)
```bash
# Install with Go
go get github.com/sachaos/todoist

# Or download binary from GitHub releases
# https://github.com/sachaos/todoist/releases
```

## Initial Configuration

### Get Your API Token
1. Log in to Todoist web app
2. Navigate to Settings → Integrations
3. Copy your API token from the "API token" section
4. Or direct link: https://todoist.com/app/settings/integrations/developer

### Configure the CLI
```bash
# For @sachinraja/todoist-cli
todoist configure
# Enter your API token when prompted

# For Python version - set environment variable
export TODOIST_API_TOKEN="your_api_token_here"

# Or add to ~/.bashrc or ~/.zshrc for persistence
echo 'export TODOIST_API_TOKEN="your_api_token_here"' >> ~/.bashrc
```

### Verify Installation
```bash
todoist --version
todoist list  # Should show your tasks
todoist sync  # Sync with Todoist servers
```

## Color Scheme Configuration

### Understanding Todoist Priority Colors
- **Priority 1 (p1)**: Red (#DC322F) - Urgent/Critical tasks
- **Priority 2 (p2)**: Orange/Yellow (#FF9500) - Important tasks
- **Priority 3 (p3)**: Blue (#4271AE) - Normal priority tasks  
- **Priority 4 (p4)**: Gray/Default (#999999) - Low priority/no priority

### Terminal Color Configuration

#### Bash/Zsh Configuration (~/.bashrc or ~/.zshrc)
```bash
# Todoist Color Variables
export TODOIST_P1_COLOR='\033[0;31m'  # Red for Priority 1
export TODOIST_P2_COLOR='\033[0;33m'  # Yellow for Priority 2
export TODOIST_P3_COLOR='\033[0;34m'  # Blue for Priority 3
export TODOIST_P4_COLOR='\033[0;37m'  # Light Gray for Priority 4
export TODOIST_OVERDUE='\033[0;35m'   # Magenta for overdue
export TODOIST_RESET='\033[0m'        # Reset color

# Enhanced colored output function
todoist_colored() {
  todoist "$@" | while IFS= read -r line; do
    if [[ $line == *"overdue"* ]]; then
      echo -e "${TODOIST_OVERDUE}$line${TODOIST_RESET}"
    elif [[ $line == *"p1"* ]] || [[ $line == *"Priority 1"* ]]; then
      echo -e "${TODOIST_P1_COLOR}$line${TODOIST_RESET}"
    elif [[ $line == *"p2"* ]] || [[ $line == *"Priority 2"* ]]; then
      echo -e "${TODOIST_P2_COLOR}$line${TODOIST_RESET}"
    elif [[ $line == *"p3"* ]] || [[ $line == *"Priority 3"* ]]; then
      echo -e "${TODOIST_P3_COLOR}$line${TODOIST_RESET}"
    else
      echo "$line"
    fi
  done
}

# Alias for colored output
alias tdc='todoist_colored'
```

### Terminal Emulator Color Profiles

#### iTerm2 Profile Settings
```xml
<!-- Add to iTerm2 Preferences → Profiles → Colors -->
ANSI Colors:
- Black: #000000
- Red (Bright): #DC322F     <!-- Priority 1 -->
- Green: #859900
- Yellow (Bright): #FF9500   <!-- Priority 2 -->
- Blue (Bright): #4271AE     <!-- Priority 3 -->
- Magenta: #D33682           <!-- Overdue -->
- Cyan: #2AA198
- White: #999999             <!-- Priority 4/Default -->
```

#### VS Code Terminal Settings (settings.json)
```json
{
  "workbench.colorCustomizations": {
    "terminal.ansiRed": "#DC322F",
    "terminal.ansiBrightRed": "#DC322F",
    "terminal.ansiYellow": "#B58900",
    "terminal.ansiBrightYellow": "#FF9500",
    "terminal.ansiBlue": "#268BD2", 
    "terminal.ansiBrightBlue": "#4271AE",
    "terminal.ansiMagenta": "#D33682",
    "terminal.ansiWhite": "#93A1A1",
    "terminal.ansiBrightWhite": "#999999",
    "terminal.background": "#002B36",
    "terminal.foreground": "#839496"
  }
}
```

#### Windows Terminal Settings
```json
{
  "schemes": [
    {
      "name": "Todoist",
      "red": "#DC322F",
      "brightRed": "#DC322F",
      "yellow": "#B58900",
      "brightYellow": "#FF9500", 
      "blue": "#268BD2",
      "brightBlue": "#4271AE",
      "brightWhite": "#999999",
      "background": "#002B36",
      "foreground": "#839496"
    }
  ]
}
```

## Configuration Files

### ~/.todoistrc (JSON Configuration)
```json
{
  "token": "your_api_token_here",
  "color": true,
  "cache": true,
  "cacheExpiry": 300,
  "indent": 2,
  "dateFormat": "MM/DD/YYYY",
  "timeFormat": "12h",
  "timezone": "America/New_York",
  "defaultProject": "Inbox",
  "defaultPriority": 4,
  "defaultFilter": "today | overdue",
  "showProjectNames": true,
  "showLabels": true,
  "completionSound": false
}
```

### Environment Variables
```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.bash_profile
export TODOIST_API_TOKEN="your_token_here"
export TODOIST_DEFAULT_PROJECT="Inbox"
export TODOIST_DEFAULT_PRIORITY="4"
export TODOIST_COLOR_OUTPUT="true"
export TODOIST_DATE_FORMAT="MM/DD/YYYY"
export TODOIST_TIMEZONE="America/New_York"
```

## Essential Commands & Usage

### Basic Task Management
```bash
# Add tasks with natural language
todoist add "Buy groceries today"
todoist add "Meeting with John tomorrow at 3pm"
todoist add "Quarterly report due next Friday p1"
todoist add "Call mom @phone #Personal"

# Add with specific attributes
todoist add "Important task" --priority 1 --date "today"
todoist add "Work task" --project "Work" --label "urgent"
todoist add "Recurring task" --date "every Monday"

# List tasks
todoist list                               # All tasks
todoist list --filter "today"              # Today's tasks
todoist list --filter "overdue"            # Overdue tasks
todoist list --filter "p1"                 # Priority 1 tasks
todoist list --filter "#Work"              # Tasks in Work project
todoist list --filter "@email"             # Tasks with email label

# Complete tasks
todoist complete [task_id]
todoist close [task_id]                    # Alias for complete

# Update tasks
todoist modify [task_id] --content "Updated task name"
todoist modify [task_id] --date "tomorrow"
todoist modify [task_id] --priority 1
todoist move [task_id] --project "New Project"

# Delete tasks
todoist delete [task_id]
```

### Advanced Filters
```bash
# Combination filters
todoist list --filter "today & p1"
todoist list --filter "(overdue | today) & #Work"
todoist list --filter "due before: tomorrow & !#Personal"
todoist list --filter "assigned to: me & p1 | p2"
todoist list --filter "created before: -7 days"
todoist list --filter "@waiting | @delegated"

# Date-based filters
todoist list --filter "due today"
todoist list --filter "due this week"
todoist list --filter "due in next 7 days"
todoist list --filter "no due date"
```

### Project Management
```bash
# List all projects
todoist projects
todoist projects list

# Add new project
todoist project add "New Project Name"

# Archive/delete project  
todoist project archive [project_id]
todoist project delete [project_id]
```

### Label Management
```bash
# List all labels
todoist labels
todoist labels list

# Add new label
todoist label add "urgent"
todoist label add "waiting"

# Delete label
todoist label delete [label_id]
```

## Productivity Aliases & Functions

### Shell Aliases (~/.bashrc or ~/.zshrc)
```bash
# Quick aliases
alias td='todoist'
alias tda='todoist add'
alias tdl='todoist list'
alias tdc='todoist complete'
alias tds='todoist sync'

# Filtered views
alias td-today='todoist list --filter "today | overdue"'
alias td-tomorrow='todoist list --filter "tomorrow"'
alias td-week='todoist list --filter "7 days"'
alias td-work='todoist list --filter "#Work"'
alias td-personal='todoist list --filter "#Personal"'
alias td-urgent='todoist list --filter "p1"'
alias td-waiting='todoist list --filter "@waiting"'
alias td-inbox='todoist list --filter "#Inbox"'
alias td-no-date='todoist list --filter "no date"'

# Quick add functions
td-meeting() {
  todoist add "Meeting: $1 @meeting p2 #Work today"
}

td-email() {
  todoist add "Email: $1 @email p3 today"
}

td-call() {
  todoist add "Call: $1 @phone p3 today"
}

td-bug() {
  todoist add "Bug: $1 @code p1 #Development today"
}

td-idea() {
  todoist add "Idea: $1 @ideas p4 #Someday"
}
```

### Daily Review Script
```bash
#!/bin/bash
# ~/.local/bin/todoist-daily-review

echo "======================================"
echo "         DAILY TASK REVIEW            "
echo "======================================"
echo ""

echo "📌 OVERDUE TASKS:"
todoist list --filter "overdue" | head -10
echo ""

echo "🔴 TODAY'S HIGH PRIORITY (P1):"
todoist list --filter "today & p1"
echo ""

echo "🟡 TODAY'S MEDIUM PRIORITY (P2):"
todoist list --filter "today & p2"
echo ""

echo "🔵 OTHER TODAY'S TASKS:"
todoist list --filter "today & p3 | today & p4"
echo ""

echo "📅 TOMORROW'S TASKS:"
todoist list --filter "tomorrow" | head -5
echo ""

echo "📊 STATISTICS:"
echo "Total tasks today: $(todoist list --filter 'today' | wc -l)"
echo "Overdue tasks: $(todoist list --filter 'overdue' | wc -l)"
echo ""
```

### Weekly Planning Script
```bash
#!/bin/bash
# ~/.local/bin/todoist-weekly-plan

echo "======================================"
echo "         WEEKLY PLANNING              "
echo "======================================"
echo ""

for i in {0..6}; do
  if [ $i -eq 0 ]; then
    day="today"
    label="TODAY"
  elif [ $i -eq 1 ]; then
    day="tomorrow"
    label="TOMORROW"
  else
    day="in $i days"
    label="$(date -v +${i}d '+%A' 2>/dev/null || date -d "+${i} days" '+%A' 2>/dev/null)"
  fi
  
  echo "📅 $label:"
  todoist list --filter "$day"
  echo "---"
  echo ""
done
```

## Integration with Other Tools

### Alfred Workflow Integration
```bash
# Create custom Alfred workflow with these scripts
# Script filter for searching tasks
todoist list --filter "{query}" | head -10

# Action to complete task
todoist complete {query}

# Action to add task
todoist add "{query}"
```

### Polybar/i3bar Module
```ini
[module/todoist]
type = custom/script
exec = todoist list --filter "today" | wc -l
format-prefix = "📝 "
format = <label>
interval = 300
click-left = terminal -e "todoist list --filter 'today'"
```

### Tmux Status Bar
```bash
# Add to ~/.tmux.conf
set -g status-right '#[fg=yellow]📝 #(todoist list --filter "today" | wc -l) tasks | %H:%M'
```

### Git Commit Hook
```bash
#!/bin/bash
# .git/hooks/post-commit
# Auto-create task for code review

branch=$(git rev-parse --abbrev-ref HEAD)
commit=$(git log -1 --pretty=%B)

if [[ $branch == feature/* ]]; then
  todoist add "Review: $commit @code-review #Development p2 today"
fi
```

## Troubleshooting

### Common Issues & Solutions

#### API Token Issues
```bash
# Test API token
curl https://api.todoist.com/rest/v2/tasks \
  -H "Authorization: Bearer YOUR_TOKEN"

# Reset configuration
rm ~/.todoistrc
todoist configure
```

#### Sync Problems
```bash
# Force sync
todoist sync --force

# Clear cache
rm -rf ~/.todoist/cache/*
todoist sync
```

#### Colors Not Displaying
```bash
# Check terminal color support
echo $TERM  # Should show something like "xterm-256color"

# Force color output
todoist list --color always

# Test ANSI colors
echo -e "\033[0;31mRed\033[0m \033[0;33mYellow\033[0m \033[0;34mBlue\033[0m"
```

#### Permission Issues
```bash
# Fix npm global permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Reinstall
npm install -g @sachinraja/todoist-cli
```

### Debug Mode
```bash
# Enable verbose logging
todoist --verbose list
todoist --debug sync

# Check configuration
todoist config
todoist config get token
todoist config get color
```

## Advanced Features

### Batch Operations
```bash
# Complete multiple tasks
todoist list --filter "today" | grep "Done:" | awk '{print $1}' | xargs -I {} todoist complete {}

# Add multiple tasks from file
cat tasks.txt | while read task; do todoist add "$task"; done

# Bulk priority update
todoist list --filter "#Work" | awk '{print $1}' | xargs -I {} todoist modify {} --priority 2
```

### Export/Backup Tasks
```bash
#!/bin/bash
# Backup all tasks to JSON
todoist list --json > todoist-backup-$(date +%Y%m%d).json

# Export to CSV
todoist list --filter "all" | awk -F'\t' '{print $2","$3","$4}' > tasks.csv

# Backup with Python
python3 << EOF
import todoist
api = todoist.TodoistAPI('YOUR_TOKEN')
api.sync()
import json
with open('todoist-full-backup.json', 'w') as f:
    json.dump(api.state, f, indent=2)
EOF
```

### Custom Notifications
```bash
#!/bin/bash
# Desktop notification for due tasks (Linux/macOS)

overdue_count=$(todoist list --filter "overdue" | wc -l)
today_count=$(todoist list --filter "today" | wc -l)

if [ $overdue_count -gt 0 ]; then
  # macOS
  osascript -e "display notification \"You have $overdue_count overdue tasks\" with title \"Todoist\""
  # Linux
  notify-send "Todoist" "You have $overdue_count overdue tasks"
fi
```

## Quick Reference Card

### Most Used Commands
```bash
todoist add "task"                    # Add task
todoist list                          # List all tasks  
todoist list --filter "today"         # Today's tasks
todoist complete [id]                 # Complete task
todoist sync                          # Sync with server
todoist projects                      # List projects
todoist labels                        # List labels
todoist modify [id] --priority 1      # Change priority
todoist modify [id] --date tomorrow   # Reschedule
todoist delete [id]                   # Delete task
```

### Filter Cheat Sheet
```bash
today               # Due today
tomorrow            # Due tomorrow
overdue            # Past due date
no date            # No due date
p1, p2, p3, p4     # By priority
#ProjectName       # By project
@labelname         # By label
next 7 days        # Due in next week
created: today     # Created today
assigned to: me    # Assigned to you
```

## Resources & Links

- Official Todoist API: https://developer.todoist.com/
- @sachinraja/todoist-cli: https://github.com/sachinraja/todoist-cli
- sachaos/todoist (Go): https://github.com/sachaos/todoist
- Todoist Python: https://github.com/Doist/todoist-python
- Todoist Filters Guide: https://todoist.com/help/articles/introduction-to-filters
- API Token Page: https://todoist.com/app/settings/integrations/developer
