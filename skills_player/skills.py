"""Skill loading, listing, and conversion utilities."""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .config import SKILLS_DIR

# Regex patterns for detecting obfuscated/dynamic selectors
_OBFUSCATED_PATTERNS = [
    r'^#[a-z]_\d+_\d+',          # React: #u_0_5_Kj
    r'^#mat-[a-z]+-\d+',         # Angular Material: #mat-input-0
    r'^#:r[a-z0-9]+:$',          # React 18+: #:r1a:
    r'^\[data-v-[a-f0-9]+\]',    # Vue scoped: [data-v-abc123]
    r'^#ember\d+',               # Ember: #ember123
    r'^\.css-[a-z0-9]{6,}',      # CSS-in-JS: .css-1a2b3c
    r'^#[a-f0-9]{8,}',           # Hash IDs: #a1b2c3d4e5
    r'^\[_ngcontent-',           # Angular: [_ngcontent-xxx]
]


def _is_obfuscated_selector(selector: str) -> bool:
    """Check if a selector looks like a dynamic/obfuscated ID."""
    for pattern in _OBFUSCATED_PATTERNS:
        if re.match(pattern, selector, re.IGNORECASE):
            return True
    return False


def load_skill(path: str | Path) -> dict[str, Any]:
    """
    Load a skill JSON file.

    Args:
        path: Path to the skill file (absolute or relative to SKILLS_DIR).

    Returns:
        Parsed skill dictionary.

    Raises:
        FileNotFoundError: If the skill file does not exist.
    """
    path = Path(path)

    # If just a name, look in skills directory
    if not path.exists() and not path.is_absolute():
        path = SKILLS_DIR / path

    # Add .json if missing
    if not path.suffix:
        path = path.with_suffix('.json')

    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")

    with open(path, encoding='utf-8') as f:
        return json.load(f)


def list_skills() -> list[dict[str, Any]]:
    """
    List all skills in the skills directory and subdirectories.

    Returns:
        List of skill metadata dictionaries.
    """
    if not SKILLS_DIR.exists():
        return []

    skills: list[dict[str, Any]] = []
    for file in sorted(SKILLS_DIR.rglob("*.json")):
        # Skip dotfiles (like .preferences.json)
        if file.name.startswith('.'):
            continue

        try:
            with open(file, encoding='utf-8') as f:
                data = json.load(f)

                # Count action steps (excluding setViewport, chrome:// navigates)
                action_steps = 0
                for step in data.get("steps", []):
                    if step.get("type") == "setViewport":
                        continue
                    step_url = step.get("url", "")
                    if step.get("type") == "navigate" and step_url.startswith("chrome://"):
                        continue
                    action_steps += 1

                # Get relative path from skills directory
                rel_path = file.relative_to(SKILLS_DIR)
                skills.append({
                    "file": str(rel_path),
                    "title": data.get("title", file.stem),
                    "description": data.get("description", ""),
                    "steps": action_steps,
                    "env_vars": list(data.get("env_vars", {}).keys()),
                    "has_extract": bool(data.get("extract_prompt")),
                })
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping {file.name}: JSON parse error - {e}", file=sys.stderr)
        except KeyError as e:
            print(f"⚠️  Skipping {file.name}: Missing key - {e}", file=sys.stderr)
        except OSError as e:
            print(f"⚠️  Skipping {file.name}: {e}", file=sys.stderr)

    return skills


def check_required_env_vars(skill: dict[str, Any]) -> list[str]:
    """
    Check which required environment variables are missing.

    Args:
        skill: The skill dictionary.

    Returns:
        List of missing environment variable names.
    """
    env_vars = skill.get("env_vars", {})
    missing: list[str] = []

    for var_name in env_vars.keys():
        if os.getenv(var_name) is None:
            missing.append(var_name)

    # Also scan the steps for {{VAR}} patterns
    steps_str = json.dumps(skill.get("steps", []))
    pattern = r'\{\{(\w+)\}\}'
    for match in re.finditer(pattern, steps_str):
        var_name = match.group(1)
        if os.getenv(var_name) is None and var_name not in missing:
            missing.append(var_name)

    return missing


def substitute_env_vars(obj: Any) -> Any:
    """
    Recursively substitute {{ENV_VAR}} placeholders with environment values.

    Args:
        obj: The object to process (str, dict, list, or other).

    Returns:
        The object with all placeholders substituted.

    Raises:
        ValueError: If an environment variable is not set.
    """
    if isinstance(obj, str):
        pattern = r'\{\{(\w+)\}\}'

        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable {var_name} is not set")
            return value

        return re.sub(pattern, replacer, obj)
    elif isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
    return obj


def get_selector_description(selectors: list[Any]) -> str | None:
    """
    Get a human-readable description of element selectors.

    Priority: aria > text > meaningful CSS. Returns None for obfuscated
    selectors that would confuse the LLM.

    Args:
        selectors: List of selector groups from Chrome Recorder.

    Returns:
        Human-readable description, or None if no good selector found.
    """
    if not selectors:
        return None

    # First pass: look for aria and text selectors (best quality)
    for selector_group in selectors:
        if isinstance(selector_group, list):
            for sel in selector_group:
                if isinstance(sel, str):
                    if sel.startswith("aria/"):
                        return f"'{sel[5:]}'"
                    elif sel.startswith("text/"):
                        return f"'{sel[5:]}'"

    # Second pass: look for meaningful CSS selectors
    first = selectors[0]
    if isinstance(first, list) and first:
        sel = first[0]
        if isinstance(sel, str):
            # Check for obfuscated selectors - skip them
            if _is_obfuscated_selector(sel):
                return None

            if sel.startswith("aria/"):
                return f"'{sel[5:]}'"
            elif sel.startswith("text/"):
                return f"'{sel[5:]}'"
            elif sel.startswith("#"):
                # Only use ID selectors that look meaningful
                return f"element with id '{sel[1:]}'"
            elif sel.startswith("."):
                # Class selectors can be useful
                return f"element with class '{sel[1:]}'"

    return None


def skill_to_task(
    skill: dict[str, Any],
    mask_passwords: bool = True,
    loose_mode: bool = False,
) -> str:
    """
    Convert a skill to a natural language task for browser-use.

    Args:
        skill: The skill dictionary (Chrome Recorder JSON format).
        mask_passwords: If True, mask password values in output.
        loose_mode: If True, provide intent-based instructions rather than
                   strict step-by-step. Lets the agent reason more freely.

    Returns:
        Natural language task string for browser-use to execute.
    """
    steps = skill.get("steps", [])
    title = skill.get("title", "Recorded Task")
    description = skill.get("description", "")

    # In loose mode, describe the goal and provide steps as hints
    if loose_mode:
        return _skill_to_loose_task(skill, mask_passwords)

    task_lines = [f"# Task: {title}"]

    if description:
        task_lines.append(f"Description: {description}")

    task_lines.extend(["", "Execute these steps in order:", ""])

    step_num = 0
    for step in steps:
        step_type = step.get("type")

        if step_type == "setViewport":
            continue

        elif step_type == "navigate":
            url = step.get("url", "")
            if url.startswith("chrome://"):
                continue
            step_num += 1
            task_lines.append(f"{step_num}. Go to: {url}")

        elif step_type == "click":
            selectors = step.get("selectors", [])
            selector_desc = get_selector_description(selectors)
            step_num += 1
            if selector_desc:
                task_lines.append(f"{step_num}. Click on {selector_desc}")
            else:
                # No good selector - describe by position/context
                task_lines.append(f"{step_num}. Click on the appropriate element")

        elif step_type == "doubleClick":
            selectors = step.get("selectors", [])
            selector_desc = get_selector_description(selectors)
            step_num += 1
            if selector_desc:
                task_lines.append(f"{step_num}. Double-click on {selector_desc}")
            else:
                task_lines.append(f"{step_num}. Double-click on the appropriate element")

        elif step_type == "change":
            value = step.get("value", "")
            selectors = step.get("selectors", [])
            selector_desc = get_selector_description(selectors)

            # Check if this looks like a password field
            is_password = any(
                "password" in str(sel).lower()
                for group in selectors
                for sel in (group if isinstance(group, list) else [group])
            )

            # Check if this is a sensitive field (email, username, etc.)
            is_sensitive = is_password or any(
                kw in str(selectors).lower()
                for kw in ["password", "email", "user", "login", "ssn", "account"]
            )

            step_num += 1
            if is_password:
                if mask_passwords:
                    display_value = "********"
                else:
                    # For sensitive fields, instruct agent to type without
                    # embedding literal value in the prompt
                    display_value = "[password value]"
                field_desc = selector_desc or "the password field"
                task_lines.append(f"{step_num}. Type '{display_value}' into {field_desc}")
            elif is_sensitive and not mask_passwords:
                field_desc = selector_desc or "the input field"
                task_lines.append(f"{step_num}. Type the appropriate credential into {field_desc}")
            else:
                field_desc = selector_desc or "the input field"
                task_lines.append(f"{step_num}. Type '{value}' into {field_desc}")

        elif step_type == "keyDown":
            key = step.get("key", "")
            step_num += 1
            task_lines.append(f"{step_num}. Press {key} key")

        elif step_type == "keyUp":
            continue

        elif step_type == "scroll":
            y = step.get("y", 0)
            x = step.get("x", 0)
            step_num += 1
            if y > 0:
                task_lines.append(f"{step_num}. Scroll down")
            elif y < 0:
                task_lines.append(f"{step_num}. Scroll up")
            else:
                task_lines.append(f"{step_num}. Scroll to position ({x}, {y})")

        elif step_type == "hover":
            selectors = step.get("selectors", [])
            selector_desc = get_selector_description(selectors)
            step_num += 1
            if selector_desc:
                task_lines.append(f"{step_num}. Hover over {selector_desc}")
            else:
                task_lines.append(f"{step_num}. Hover over the appropriate element")

        elif step_type == "waitForElement":
            selectors = step.get("selectors", [])
            selector_desc = get_selector_description(selectors)
            step_num += 1
            if selector_desc:
                task_lines.append(f"{step_num}. Wait for {selector_desc} to appear")
            else:
                task_lines.append(f"{step_num}. Wait for the page to update")

        elif step_type == "waitForExpression":
            step_num += 1
            task_lines.append(f"{step_num}. Wait for page condition")

        elif step_type == "close":
            step_num += 1
            task_lines.append(f"{step_num}. Close the tab/window")

    task_lines.extend([
        "",
        "Complete each step in sequence. Wait for the page to load between steps.",
        "If an element can't be found by the exact description, look for similar elements nearby."
    ])

    return "\n".join(task_lines)


def _skill_to_loose_task(skill: dict[str, Any], mask_passwords: bool = True) -> str:
    """
    Convert a skill to a loose/intent-based task description.

    Instead of strict step-by-step instructions, describe the goal and
    provide the recorded steps as hints for the agent to use flexibly.

    Args:
        skill: The skill dictionary.
        mask_passwords: If True, mask password values.

    Returns:
        Intent-based task string.
    """
    title = skill.get("title", "Task")
    description = skill.get("description", "")
    steps = skill.get("steps", [])

    # Extract key information from steps
    urls = []
    actions = []

    for step in steps:
        step_type = step.get("type")

        if step_type == "navigate":
            url = step.get("url", "")
            if url and not url.startswith("chrome://"):
                urls.append(url)

        elif step_type == "click":
            selectors = step.get("selectors", [])
            desc = get_selector_description(selectors)
            if desc:
                actions.append(f"click {desc}")

        elif step_type == "change":
            selectors = step.get("selectors", [])
            desc = get_selector_description(selectors)
            is_password = "password" in str(selectors).lower()
            if desc:
                if is_password:
                    actions.append(f"enter password in {desc}")
                else:
                    actions.append(f"fill in {desc}")

    # Build the loose task
    lines = [
        f"# Goal: {title}",
        "",
    ]

    if description:
        lines.append(f"{description}")
        lines.append("")

    lines.append("Complete this task using your best judgment. Here's what needs to happen:")
    lines.append("")

    if urls:
        lines.append(f"- Start at: {urls[0]}")

    # Summarize the intent
    if actions:
        lines.append(f"- Key actions: {', '.join(actions[:5])}")
        if len(actions) > 5:
            lines.append(f"  (and {len(actions) - 5} more steps)")

    lines.extend([
        "",
        "Use the page content and your reasoning to complete the goal.",
        "The exact selectors may have changed - adapt as needed.",
        "If you encounter login screens, fill in the appropriate credentials.",
    ])

    return "\n".join(lines)
