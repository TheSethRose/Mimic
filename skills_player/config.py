"""Configuration and constants for the skills player."""

import os
from pathlib import Path

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent

# Directory for storing skills
SKILLS_DIR = BASE_DIR / "skills"

# File for storing user preferences (MFA choices, etc.)
PREFERENCES_FILE = SKILLS_DIR / ".preferences.json"

# LLM Configuration (configurable via environment)
DEFAULT_LLM_PROVIDER = "openrouter"
DEFAULT_LLM_MODEL = "google/gemini-2.5-flash"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
