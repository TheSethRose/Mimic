# Product Requirements Document: Browser-Use Skill System

## Overview

A simple system to record browser interactions as reusable "skills" and replay them using browser-use's built-in `AgentHistoryList` and `rerun_history()` capabilities.

## Goals

1. **Create a skill** - Run an agent task and save the complete history as a reusable skill
2. **Replay a skill** - Execute saved skills reliably with parameter substitution

## Non-Goals

- Complex skill marketplace or sharing features
- Advanced version control or diffing
- UI/web interface (CLI only for v1)
- Multi-step branching logic or conditionals

## User Stories

### Story 1: Record a Skill
As a user, I want to run an agent task and save it so I can replay it later.

**Acceptance Criteria:**
- Start recording with `python agents/skill_recorder.py --name "skill-name" --task "Describe what to do"`
- Browser opens in visible mode
- Agent executes the task autonomously
- Complete history saved to `skills/skill-name.json`
- Metadata includes name, description, timestamp, and parameters

### Story 2: Replay a Skill
As a user, I want to replay a recorded skill with different parameters.

**Acceptance Criteria:**
- Run skill with `python agents/skill_player.py --skill "skill-name" --params '{"url": "..."}'`
- System loads skill from `skills/skill-name.json`
- Parameter substitution happens before replay
- Uses `agent.rerun_history()` for execution
- Returns structured result with success/failure status

## Technical Design

### Skill File Format

Skills leverage browser-use's native `AgentHistoryList.save_to_file()` format with metadata wrapper:

```json
{
  "name": "github-stars",
  "description": "Get star count from a GitHub repository",
  "created_at": "2025-12-03T10:00:00Z",
  "task": "Go to {{url}} and extract the star count",
  "parameters": {
    "url": {
      "type": "string",
      "description": "GitHub repository URL",
      "required": true,
      "default": "https://github.com/browser-use/browser-use"
    }
  },
  "history": [
    // Native AgentHistory items from AgentHistoryList.model_dump()
  ]
}
```

### Components

#### 1. Skill Recorder (`agents/skill_recorder.py`)

Records browser interactions by running an agent and saving its history.

```
Usage:
  python agents/skill_recorder.py --name "skill-name" --task "Your task description"

Options:
  --name         Skill name (used for filename)
  --task         The task for the agent to perform
  --description  Optional description of what the skill does
  --headless     Run in headless mode (default: visible)

Flow:
  1. Initialize browser (visible by default)
  2. Create and run Agent with the provided task
  3. Wait for agent completion
  4. Extract parameters from task ({{variable}} syntax)
  5. Save skill JSON with metadata + history.model_dump()
```

#### 2. Skill Player (`agents/skill_player.py`)

Replays recorded skills using browser-use's `rerun_history()` method.

```
Usage:
  python agents/skill_player.py --skill "skill-name" --params '{"url": "..."}'

Options:
  --skill        Skill name to replay
  --params       JSON string of parameters to substitute
  --headless     Run in headless mode (default: visible)
  --max-retries  Max retries per step (default: 3)

Flow:
  1. Load skill from skills/skill-name.json
  2. Substitute {{param}} placeholders in URLs and text
  3. Use AgentHistoryList.load_from_dict() to parse history
  4. Call agent.rerun_history() with loaded history
  5. Display results and any errors
```

#### 3. Skill Storage

```
skills/
  github-stars.json
  hn-top-posts.json
  amazon-product.json
```

### Key Browser-Use Integration

The skill system leverages these existing browser-use features:

1. **`history.save_to_file()`** - Native JSON serialization of agent history
2. **`AgentHistoryList.load_from_file()`** - Reconstruct history from JSON
3. **`agent.rerun_history()`** - Smart replay with element re-matching
4. **`AgentHistory`** - Contains model_output, result, state, metadata

### Parameter Substitution

Simple `{{variable}}` syntax replacement before replay:
- Task: `"Go to {{url}} and extract data"` → `"Go to https://example.com and extract data"`
- URLs in navigate actions get substituted
- Text in input actions get substituted

## Implementation Plan

### Phase 1: Basic Recording
- [x] Create `skill_recorder.py`
- [x] Run agent and capture history
- [x] Save with metadata wrapper
- [x] Extract parameters from task

### Phase 2: Basic Playback
- [x] Create `skill_player.py`
- [x] Load skill JSON
- [x] Parameter substitution
- [x] Use rerun_history()
- [x] Display results

### Phase 3: Polish
- [ ] List available skills command
- [ ] Validate skill files
- [ ] Better error messages
- [ ] Dry-run mode

## Success Metrics

1. Can record a skill in < 2 minutes
2. Replay success rate > 80% on same site
3. Parameter substitution works for URLs
4. Clear error messages when skills fail

## Example Workflows

### Workflow 1: Create HN Top Post Skill

```bash
# Record the skill
python agents/skill_recorder.py \
  --name "hn-top-post" \
  --task "Go to https://news.ycombinator.com and extract the title of the #1 post"

# Replay (no params needed for this one)
python agents/skill_player.py --skill "hn-top-post"
```

### Workflow 2: Create GitHub Stars Skill with Parameters

```bash
# Record with a template URL
python agents/skill_recorder.py \
  --name "github-stars" \
  --task "Go to {{url}} and extract the repository star count" \
  --params '{"url": "https://github.com/browser-use/browser-use"}'

# Replay with different repo
python agents/skill_player.py \
  --skill "github-stars" \
  --params '{"url": "https://github.com/anthropics/anthropic-sdk-python"}'
```

### Workflow 3: List and Manage Skills

```bash
# List all saved skills
python agents/skill_player.py --list

# Show skill details
python agents/skill_player.py --skill "github-stars" --info
```

## Future Enhancements (Not for v1)

- Skill templates library
- Validation/testing framework
- Skill versioning
- Web UI for recording
- Skill chaining/composition
- Conditional logic based on page state
- Schedule skills to run periodically
