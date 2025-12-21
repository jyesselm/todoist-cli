---
id: ref-todoist-cli-workflow
title: Todoist CLI Workflow with Tag Expansion
date: 2025-11-21
type: capture/cli
tags:
  - reference/tool
  - topic/tool/cli
  - topic/productivity
  - topic/todoist
  - project/active
status: published
summary: Complete CLI workflow for Todoist with smart tag expansion, visual hierarchy, and automation scripts
updated: 2025-11-21
---

# Todoist CLI Workflow with Tag Expansion

## Visual Hierarchy System

A color-coded tag system that provides instant visual context while maintaining CLI efficiency.

### Color Meanings

| Color | Purpose | Tags | Usage |
|-------|---------|------|-------|
| 🔴 **RED** | Needs attention | `@lab`, `@urgent`, `@focus` | Critical items requiring immediate action or deep work |
| 🟢 **GREEN** | Action types | `@coding`, `@writing`, `@analysis`, `@teaching`, `@review`, `@refactor` | Type of work being performed |
| 🔵 **BLUE** | Projects | `@dms`, `@motif`, `@pka`, `@labcode`, `@rnamake` | Specific research or code projects |
| 🟡 **YELLOW** | Quick/Admin | `@quick`, `@admin` | Fast tasks, administrative work |
| ⚫ **GRAY** | Blocked | `@waiting` | De-emphasized items pending external input |

### Complete Tag Reference

#### Location Tags
- `@lab` - Laboratory work
- `@home` - Home tasks
- `@office` - Office-specific
- `@online` - Remote/virtual tasks

#### Work Type Tags
- `@coding` - Programming tasks
- `@writing` - Documentation, papers
- `@analysis` - Data analysis, simulations
- `@admin` - Administrative tasks
- `@refactor` - Code improvements
- `@review` - Review tasks
- `@teaching` - Teaching-related

#### Project Tags
- `@dms` - DMS project
- `@motif` - Motif analysis
- `@pka` - PKA related
- `@labcode` - Lab code maintenance
- `@rnamake` - RNAmake project

#### Priority/Status Tags
- `@quick` - <15 minute tasks
- `@focus` - Deep work required
- `@waiting` - Blocked on others
- `@urgent` - Time-sensitive

## Smart Tag Expansion Script

Create `~/bin/t` for intelligent tag expansion:

```bash
#!/usr/bin/env bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Tag expansion mappings
declare -A tag_map=(
    # Locations (single letter)
    ["@l"]="@lab"
    ["@h"]="@home"
    ["@o"]="@office"
    
    # Work types (single/double letter)
    ["@c"]="@coding"
    ["@w"]="@writing"
    ["@a"]="@analysis"
    ["@ad"]="@admin"
    ["@r"]="@refactor"
    ["@re"]="@review"
    ["@t"]="@teaching"
    
    # Projects (single/double letter)
    ["@d"]="@dms"
    ["@m"]="@motif"
    ["@p"]="@pka"
    ["@lc"]="@labcode"
    ["@rn"]="@rnamake"
    
    # Status (single letter)
    ["@q"]="@quick"
    ["@f"]="@focus"
    ["@x"]="@waiting"
    ["@u"]="@urgent"
    
    # Project shortcuts
    ["#r"]="#Research"
    ["#t"]="#Teaching"
    ["#p"]="#Papers"
    ["#pr"]="#Personal"
)

# Function to expand all shortcuts in a string
expand_tags() {
    local input="$*"
    local expanded="$input"
    
    # Replace each shortcut with its full version
    for short in "${!tag_map[@]}"; do
        full="${tag_map[$short]}"
        # Use word boundaries to avoid partial matches
        expanded=$(echo "$expanded" | sed -E "s/${short}(\s|$)/${full}\1/g")
    done
    
    echo "$expanded"
}

# Function to show available shortcuts
show_shortcuts() {
    echo -e "${BLUE}═══ Tag Shortcuts ═══${NC}\n"
    
    echo -e "${RED}Priority/Location:${NC}"
    echo "  @l → @lab      @h → @home     @o → @office"
    echo "  @u → @urgent   @f → @focus    @q → @quick"
    echo ""
    
    echo -e "${GREEN}Work Types:${NC}"
    echo "  @c → @coding   @w → @writing  @a → @analysis"
    echo "  @r → @refactor @re → @review  @t → @teaching"
    echo "  @ad → @admin"
    echo ""
    
    echo -e "${BLUE}Projects:${NC}"
    echo "  @d → @dms      @m → @motif    @p → @pka"
    echo "  @lc → @labcode @rn → @rnamake"
    echo ""
    
    echo -e "${YELLOW}Todoist Projects:${NC}"
    echo "  #r → #Research #t → #Teaching #p → #Papers"
}

# Function to suggest tags based on content
suggest_tags() {
    local content="$1"
    local suggestions=""
    
    # Keyword-based suggestions
    case "$content" in
        *RNA*|*DNA*|*structure*|*simulation*|*GROMACS*)
            suggestions="@lab @analysis" ;;
        *paper*|*manuscript*|*writing*|*draft*)
            suggestions="@writing @focus" ;;
        *fix*|*bug*|*debug*|*optimize*)
            suggestions="@coding @refactor" ;;
        *meeting*|*email*|*review*)
            suggestions="@admin @quick" ;;
        *teach*|*lecture*|*students*)
            suggestions="@teaching" ;;
    esac
    
    if [ -n "$suggestions" ]; then
        echo -e "${YELLOW}💡 Suggested tags: $suggestions${NC}"
        read -p "Add these? (y/n/skip): " -n 1 -r
        echo
        case "$REPLY" in
            [Yy]) echo "$suggestions" ;;
            *) echo "" ;;
        esac
    fi
}

# Parse command line options
case "$1" in
    --help|-h)
        echo "Todoist CLI Helper"
        echo "=================="
        echo "Usage:"
        echo "  t [task]     Add task with tag expansion"
        echo "  t            Show today's tasks"
        echo "  t -l         List all shortcuts"
        echo "  t -h         Show this help"
        echo ""
        show_shortcuts
        exit 0
        ;;
    --list|-l|shortcuts)
        show_shortcuts
        exit 0
        ;;
    "")
        # No arguments - show today's tasks with formatting
        echo -e "${BLUE}═══ Today's Tasks ═══${NC}"
        todoist list --filter "today | overdue"
        exit 0
        ;;
esac

# Main task addition logic
original="$*"
expanded=$(expand_tags "$original")

# Check for auto-suggestions (unless tags already present)
if [[ ! "$expanded" =~ @ ]]; then
    suggested=$(suggest_tags "$expanded")
    if [ -n "$suggested" ]; then
        expanded="$expanded $suggested"
    fi
fi

# Show expansion if different
if [ "$original" != "$expanded" ]; then
    echo -e "${GRAY}📝 Input:    $original${NC}"
    echo -e "${GREEN}➜  Expanded: $expanded${NC}"
fi

# Add to Todoist
todoist quick "$expanded"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Task added successfully!${NC}"
else
    echo -e "${RED}❌ Failed to add task${NC}"
    exit 1
fi
```

## Shell Configuration

Add to your `.zshrc` or `.bashrc`:

```bash
# Make script executable
chmod +x ~/bin/t

# Core aliases
alias ta="t"                                    # task add
alias tl="todoist list"                        # list tasks
alias tc="todoist close"                       # complete task
alias today="todoist list --filter 'today | overdue'"
alias tomorrow="todoist list --filter 'tomorrow'"
alias week="todoist list --filter '7 days'"

# Project-specific views
alias tlab="todoist list --filter '@lab'"
alias tfocus="todoist list --filter '@focus'"
alias tquick="todoist list --filter '@quick'"

# Fuzzy task selection with fzf
tselect() {
    todoist list --all --json | \
    jq -r '.[] | "\(.id) | [\(.project)] \(.content) \(.labels // [] | map("@" + .) | join(" "))"' | \
    fzf --ansi --preview-window=hidden | \
    cut -d'|' -f1
}

# Complete task with fuzzy search
tcomplete() {
    local task_id=$(tselect)
    if [[ -n "$task_id" ]]; then
        todoist close "$task_id" && echo "✓ Task completed!"
    fi
}

# Batch task functions
monday_setup() {
    t "Review weekend simulation results @a @l @d"
    t "Update lab notebook @w @q"
    t "Check and respond to emails @ad @q @o"
    t "Plan week priorities @f @ad"
    echo "📅 Monday tasks added!"
}

friday_wrap() {
    t "Clean up code repos @c @q"
    t "Submit cluster jobs for weekend @l @q"
    t "Update project status notes @w @q"
    echo "🎉 Friday wrap-up tasks added!"
}
```

## Usage Examples

### Basic Usage
```bash
# Add task with shortcut expansion
t Fix RNA visualization bug @c @l @d p1
# Expands to: Fix RNA visualization bug @coding @lab @dms p1

# View today's tasks
t

# Show available shortcuts
t -l

# Quick task additions
t Email advisor about results @ad @q     # → @admin @quick
t Debug GROMACS simulation @c @a @u      # → @coding @analysis @urgent
```

### Advanced Workflows
```bash
# Morning routine
t "Morning email check @ad @q" && \
t "Review yesterday's results @a @l" && \
t "Plan today's experiments @f @l"

# Project batch add
for task in "Write methods section" "Create figures" "Format references"; do
    t "$task @w @f #Papers due:Friday"
done

# Interactive completion
tcomplete  # Opens fuzzy finder to select and complete tasks
```

## Tips and Best Practices

1. **Single Letter Speed**: Use single letters for common tags during rapid entry
2. **Combine Tags Logically**: `@l @a @f` = lab analysis requiring focus
3. **Use Projects for Context**: `#Research` for research tasks, `#Teaching` for courses
4. **Priority Levels**: 
   - p1: Must do today
   - p2: Should do this week
   - p3: Nice to have
5. **Time Estimates**: Add estimates like `~30m` or `~2h` in task descriptions
6. **Due Dates**: Use natural language: `today`, `tomorrow`, `Friday`, `every Monday`

## Automation Ideas

### Daily Standup Generator
```bash
standup() {
    echo "=== Daily Standup ==="
    echo "Yesterday completed:"
    todoist list --filter "completed:yesterday" | head -5
    echo -e "\nToday's focus:"
    todoist list --filter "today & @focus"
    echo -e "\nBlockers:"
    todoist list --filter "@waiting"
}
```

### Weekly Review
```bash
weekly_review() {
    echo "Tasks completed this week: $(todoist list --filter 'completed:7 days' | wc -l)"
    echo "High priority remaining:"
    todoist list --filter "p1 & !today"
    echo "Waiting items:"
    todoist list --filter "@waiting"
}
```

## Troubleshooting

- **Tags not expanding**: Check for typos in shortcuts, ensure word boundaries
- **Colors not showing**: Enable color support in terminal, check $TERM variable
- **Todoist CLI errors**: Run `todoist sync` to refresh local cache
- **Performance issues**: Consider limiting `todoist list` with date filters

## References

- [Todoist CLI Documentation](https://github.com/sachaos/todoist)
- [Todoist Filters Guide](https://todoist.com/help/articles/introduction-to-filters)
- [fzf Integration](https://github.com/junegunn/fzf)
