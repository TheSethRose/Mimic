"""LLM configuration for workflow-use.

Provides a unified way to get the configured LLM instance using OpenRouter.
"""

import os

from browser_use.llm.base import BaseChatModel
from browser_use.llm.openrouter.chat import ChatOpenRouter


# Default model configuration
DEFAULT_LLM_MODEL = 'google/gemini-2.5-flash'


def get_llm(model: str | None = None) -> BaseChatModel:
    """
    Get a configured LLM instance using OpenRouter.

    Args:
        model: Model name to use. Defaults to LLM_MODEL env var or google/gemini-2.5-flash.

    Returns:
        Configured ChatOpenRouter instance.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. "
            "Please add it to your .env file or set it as an environment variable."
        )

    model_name = model or os.getenv('LLM_MODEL', DEFAULT_LLM_MODEL)

    return ChatOpenRouter(
        model=model_name,
        api_key=api_key,
    )
