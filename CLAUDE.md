# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Mimic** is a browser automation framework that combines deterministic workflow execution with AI-powered self-healing. Record workflows once, run them forever.

## Repository Structure

```
Mimic/
├── workflows/              # Python workflow engine (main code)
│   ├── cli.py              # CLI entry point
│   ├── workflow_use/       # Core workflow library
│   │   ├── workflow/       # Workflow execution & semantic executor
│   │   ├── controller/     # Browser controller
│   │   ├── recorder/       # Workflow recorder
│   │   ├── schema/         # Pydantic models
│   │   ├── storage/        # Workflow persistence
│   │   ├── healing/        # Self-healing logic
│   │   └── mcp/            # Model Context Protocol server
│   ├── storage/            # Stored workflows & metadata
│   ├── examples/           # Example scripts
│   └── tests/              # Test suite
├── .github/                # GitHub config, Copilot instructions/skills
└── .env                    # Environment configuration
```

## Development Commands

### Setup Environment

```bash
# Create virtual environment
cd workflows
uv venv --python 3.11
source .venv/bin/activate
uv sync
```

### Run Workflow CLI

```bash
cd workflows

# List stored workflows
python cli.py list

# Run a stored workflow
python cli.py run-stored-workflow <workflow-id>

# Run with a prompt (uses LLM to fill inputs)
python cli.py run-stored-workflow <workflow-id> --prompt "your task"

# Generate workflow from natural language
python cli.py generate --prompt "Login to my bank and get balances"

# Record a new workflow
python cli.py record --url "https://example.com" --task "Login and extract data"
```

### Run Tests

```bash
cd workflows
uv run pytest -vxs tests/
```

## LLM Configuration

Mimic uses OpenRouter for LLM access. Configure in `.env`:

```bash
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp  # or other model
```

### Using LLM in Code

```python
from langchain_openai import ChatOpenAI
import os

llm = ChatOpenAI(
    model=os.getenv('OPENROUTER_MODEL', 'google/gemini-2.0-flash-exp'),
    api_key=os.getenv('OPENROUTER_API_KEY'),
    base_url='https://openrouter.ai/api/v1',
)
```

## Key Concepts

### Workflows

Workflows are YAML files defining browser automation steps:

```yaml
name: Example Workflow
version: "1.0"
inputs:
  - name: username
    type: string
    required: true
steps:
  - type: navigation
    url: "https://example.com"
  - type: click
    target_text: "Login"
  - type: input
    target_text: "Username"
    value: "{username}"
```

### Semantic Execution

The semantic executor finds elements by meaning, not just selectors:
1. **target_text** - Human-readable element description
2. **Semantic mapping** - Extracts interactive elements with context
3. **Multi-strategy matching** - Text → CSS → XPath → LLM fallback

### Self-Healing

When steps fail:
1. Refresh semantic mapping
2. Try alternative selectors
3. Use LLM to find correct element
4. Fall back to full browser-use agent

## Architecture

### Workflow Execution Flow

1. **Load workflow** → Parse YAML, resolve inputs
2. **For each step:**
   - Build semantic mapping of page elements
   - Match target_text to element
   - Execute action (click, input, navigate, extract)
   - Verify success
   - Retry with healing if failed
3. **Return results** → Extracted content, screenshots, errors

### Key Files

| File | Purpose |
|------|---------|
| `cli.py` | CLI commands and orchestration |
| `workflow_use/workflow/service.py` | Main workflow executor |
| `workflow_use/workflow/semantic_executor.py` | Semantic element finding & execution |
| `workflow_use/controller/service.py` | Browser control via CDP |
| `workflow_use/schema/workflow.py` | Workflow YAML schema |
| `workflow_use/storage/service.py` | Workflow persistence |

## Environment Variables

Required in `.env`:

```bash
# LLM Provider (required)
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp

# Workflow-specific credentials (auto-loaded for matching inputs)
PNC_USER_ID=your-username
PNC_PASSWORD=your-password
# Add other credentials as needed
```

## Code Style

- **Python**: 4-space indentation, type hints, async/await
- **Pydantic v2**: All models use `model_config = ConfigDict(...)`
- **Logging**: Use `logger = logging.getLogger(__name__)`
- **Async**: All browser operations are async

## Common Tasks

### Add a New Workflow Step Type

1. Define step model in `workflow_use/schema/workflow.py`
2. Add executor method in `workflow_use/workflow/semantic_executor.py`
3. Register in `WorkflowService._execute_step()`

### Debug Workflow Execution

```bash
# Run with verbose logging
PYTHONPATH=. python cli.py run-stored-workflow <id> 2>&1 | tee debug.log
```

### Store Credentials Securely

1. Add to `.env` file (never commit)
2. Reference in workflow inputs: `default: "$env:CREDENTIAL_NAME"`
3. CLI auto-loads matching environment variables

## Testing

```bash
cd workflows

# Run all tests
uv run pytest -vxs tests/

# Run specific test
uv run pytest -vxs tests/test_workflow_execution.py

# Run with coverage
uv run pytest --cov=workflow_use tests/
```
