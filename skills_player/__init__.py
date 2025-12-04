"""
Mimic - Browser Automation with Muscle Memory.

Turn Chrome Recordings into Unbreakable AI Agents.

This package plays back browser automation skills with:
- Environment variable substitution for credentials
- Interactive MFA/OTP prompts
- User preference persistence
- Data extraction capabilities
- Loose mode for adaptive execution

Configuration via environment variables:
- LLM_PROVIDER: openrouter (default), openai, anthropic
- LLM_MODEL: Model name (default: google/gemini-2.5-flash)
"""

from .config import LLM_MODEL, LLM_PROVIDER
from .skills import list_skills, load_skill, skill_to_task


def play_skill(*args, **kwargs):
    """Lazy import wrapper for play_skill to speed up CLI startup."""
    from .player import play_skill as _play_skill
    return _play_skill(*args, **kwargs)


def create_interactive_tools(*args, **kwargs):
    """Lazy import wrapper for create_interactive_tools."""
    from .tools import create_interactive_tools as _create_tools
    return _create_tools(*args, **kwargs)


__all__ = [
    "play_skill",
    "list_skills",
    "load_skill",
    "skill_to_task",
    "create_interactive_tools",
    "LLM_PROVIDER",
    "LLM_MODEL",
]
