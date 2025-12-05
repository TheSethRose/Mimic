# Mimic

**Browser Automation with Muscle Memory.**

Deterministic, Self-Healing Workflows (RPA 2.0).

---

Standard automation breaks the moment a website changes. Mimic combines deterministic workflow execution with AI-powered self-healing—adapting to layout shifts, healing broken selectors, and falling back to intelligent agents when needed.

**Record once. Run forever.**

## Features

- 🤖 **Natural Language Generation** — Describe what you want, get a reusable workflow
- 🧠 **Self-Healing Selectors** — Multi-strategy element finding (semantic text → CSS → XPath)
- ⚡ **Deterministic Execution** — Direct CDP execution for speed (no LLM per step)
- 🔄 **Agent Fallback** — Falls back to browser-use agent when steps fail
- 📊 **Variable Extraction** — Automatic parameterization of dynamic values
- 🔒 **Secure Credentials** — Environment variable substitution for sensitive data

## Quick Start

### 1. Setup Environment

```bash
cd workflows
uv sync
source .venv/bin/activate  # mac/linux
playwright install chromium
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your API key:

```env
# Required: OpenRouter API key
OPENROUTER_API_KEY=your_key_here

# Optional: Configure model (defaults to google/gemini-2.0-flash-exp)
# OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

### 3. Create Workflows

**Generate from Natural Language:**

```bash
python cli.py generate-workflow "Login to GitHub and star the browser-use repo"
```

### 4. Run Workflows

```bash
# List all workflows
python cli.py list

# Run a stored workflow
python cli.py run-stored-workflow <workflow-id>

# Run with AI assistance (for form filling)
python cli.py run-stored-workflow <workflow-id> --prompt "fill with example data"
```

## CLI Commands

```bash
# Workflow Generation
python cli.py generate-workflow "Your task description"

# Workflow Management
python cli.py list                         # List all stored workflows
python cli.py workflow-info <id>           # View workflow details
python cli.py delete-workflow <id>         # Delete a workflow

# Workflow Execution
python cli.py run-workflow <path>          # Run YAML workflow file
python cli.py run-stored-workflow <id>     # Run from storage
python cli.py run-stored-workflow <id> --prompt "..."  # Run with AI filling inputs
```

## How It Works

1. **Record/Generate** — Create workflows via browser recording or natural language
2. **Store** — Workflows saved as YAML/JSON with semantic targeting
3. **Execute** — Deterministic CDP execution (fast, no LLM cost per step)
4. **Self-Heal** — Multi-strategy element finding adapts to page changes
5. **Fallback** — If a step fails, browser-use agent takes over intelligently

## Programmatic Usage

```python
from workflow_use.healing.service import HealingService
from workflow_use.storage.service import WorkflowStorageService
from workflow_use.llm import get_llm

llm = get_llm()  # Uses OpenRouter with google/gemini-2.5-flash by default
healing_service = HealingService(llm=llm)
storage_service = WorkflowStorageService()

# Generate workflow from natural language
workflow = await healing_service.generate_workflow_from_prompt(
    prompt="Fill contact form on example.com",
    agent_llm=llm,
    extraction_llm=llm,
)

# Save and retrieve
metadata = storage_service.save_workflow(workflow, generation_mode='browser_use')
loaded = storage_service.get_workflow(metadata.id)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key (required) | — |
| `LLM_MODEL` | Model to use | `google/gemini-2.5-flash` |

## Project Structure

```
Mimic/
├── workflows/              # Python workflow engine
│   ├── cli.py              # CLI entry point
│   ├── workflow_use/       # Core package
│   │   ├── workflow/       # Execution & semantic executor
│   │   ├── controller/     # Browser control via CDP
│   │   ├── healing/        # Self-healing & generation
│   │   ├── schema/         # Workflow schemas (Pydantic)
│   │   ├── storage/        # Persistence
│   │   ├── recorder/       # Recording service
│   │   └── mcp/            # Model Context Protocol server
│   ├── storage/            # Stored workflows
│   └── tests/              # Test suite
└── .env                    # Configuration
```

## License

MIT

---

**Mimic** — Record once. Run forever.
