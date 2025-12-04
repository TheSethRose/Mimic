# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a development workspace for building browser automation agents using the browser-use library. The `/source/` directory contains the browser-use library codebase, and the `/agents/` directory contains custom agent implementations.

## Repository Structure

- **`/source/`** - Full browser-use library source code (from https://github.com/browser-use/browser-use)
  - See `/source/CLAUDE.md` for library development guidance
  - Contains all core browser automation components
- **`/agents/`** - Custom agent scripts and implementations
  - User-created agents that leverage the browser-use library
  - Example agents demonstrating various use cases
- **`.env`** - Environment configuration (API keys, etc.)

## Development Commands

**Setup environment:**
```bash
uv venv --python 3.11
source .venv/bin/activate
uv sync
```

**Install browser-use in editable mode from source:**
```bash
uv pip install -e ./source
```

**Run agent scripts:**
```bash
# Run a specific agent
uv run agents/browser.py

# Run with command-line task
uv run agents/browser.py "your task here"
```

**Work with the browser-use library:**
```bash
# Run library tests
cd source && uv run pytest -vxs tests/ci

# Type checking
cd source && uv run pyright

# Linting/formatting
cd source && uv run ruff check --fix && uv run ruff format
```

## Building Agents

When creating new agents in `/agents/`, follow these patterns:

**Basic agent structure:**
```python
import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent, Browser
from browser_use.llm.openrouter.chat import ChatOpenRouter

load_dotenv()

async def main():
    # Initialize LLM
    llm = ChatOpenRouter(
        model='google/gemini-2.5-flash',
        api_key=os.getenv('OPENROUTER_API_KEY'),
    )

    # Initialize Browser
    browser = Browser(headless=False)

    # Create and run agent
    agent = Agent(
        task="Your task here",
        llm=llm,
        browser=browser,
    )

    history = await agent.run()

    # Process results
    print(f"Success: {history.is_successful()}")
    print(f"Result: {history.final_result()}")

if __name__ == '__main__':
    asyncio.run(main())
```

**Key agent development patterns:**

- Use `Browser(headless=False)` during development to see the browser in action
- Switch to `headless=True` for production/automated runs
- Always load API keys from `.env` file using `python-dotenv`
- Use `history` object to access results: `.final_result()`, `.urls()`, `.errors()`, `.screenshots()`
- For production, consider `Browser(use_cloud=True)` for better performance and stealth

## LLM Provider Configuration

**OpenRouter (recommended for development):**
```python
from browser_use.llm.openrouter.chat import ChatOpenRouter

llm = ChatOpenRouter(
    model='google/gemini-2.5-flash',
    api_key=os.getenv('OPENROUTER_API_KEY'),
)
```

**Browser Use optimized model (recommended for production):**
```python
from browser_use import ChatBrowserUse

llm = ChatBrowserUse()  # Requires BROWSER_USE_API_KEY in .env
```

**Other providers:**
- OpenAI: `from browser_use.llm.openai.chat import ChatOpenAI`
- Anthropic: `from browser_use.llm.anthropic.chat import ChatAnthropic`
- Google: `from browser_use.llm.google.chat import ChatGoogle`

## Environment Variables

Required in `.env` file:
```bash
# Choose one LLM provider
OPENROUTER_API_KEY=your-key-here
# OR
BROWSER_USE_API_KEY=your-key-here  # For ChatBrowserUse
# OR
OPENAI_API_KEY=your-key-here
# OR
ANTHROPIC_API_KEY=your-key-here
```

## Agent Development Tips

**Interactive mode:**
Create agents with CLI input for rapid testing (see `agents/browser.py` for example)

**Error handling:**
```python
history = await agent.run()

if not history.is_successful():
    print("Task failed!")
    for error in history.errors():
        print(f"Error: {error}")
```

**Custom tools:**
```python
from browser_use import Tools

tools = Tools()

@tools.action('Description of what this tool does')
def custom_tool(param: str) -> str:
    return f"Result: {param}"

agent = Agent(task="...", llm=llm, browser=browser, tools=tools)
```

**Browser configuration:**
```python
browser = Browser(
    headless=False,                    # Visible browser
    window_size={'width': 1920, 'height': 1080},
    use_cloud=False,                   # Use local browser
)
```

## Common Workflows

**1. Create a new agent:**
- Copy an existing agent from `/agents/` as a template
- Modify the task and any custom logic
- Test with `uv run agents/your_agent.py`

**2. Test different LLM providers:**
- Update the LLM initialization in your agent
- Add required API key to `.env`
- Compare performance and cost

**3. Production deployment:**
- Switch to `Browser(use_cloud=True)` for stealth and scale
- Use `ChatBrowserUse()` for optimized performance
- Consider the `@sandbox()` decorator for managed infrastructure

**4. Debug agent behavior:**
- Run with `headless=False` to watch the browser
- Check `history.errors()` for failures
- Review `history.urls()` to see navigation flow
- Use screenshots: `history.screenshots()`

## Code Style

- Use async/await throughout (browser-use is fully async)
- Load environment variables with `python-dotenv`
- Use type hints for function parameters
- Keep agent logic modular and reusable
- Comment complex task logic

## Library Development

If you need to modify the browser-use library itself:
1. Navigate to `/source/`
2. Read `/source/CLAUDE.md` for development guidelines
3. Make changes following the library's architecture
4. Run tests from `/source/`: `uv run pytest -vxs tests/ci`
5. Agent scripts will automatically use the local source via editable install
