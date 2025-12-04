#!/usr/bin/env python3
"""
Mimic - Browser Automation with Muscle Memory.

Turn Chrome Recordings into Unbreakable AI Agents.

Usage:
    # Natural language - AI decides what to run
    python mimic.py "Get my Alexa shopping list"
    python mimic.py "Get my Alexa shopping list and add items to Walmart cart"
    python mimic.py "Check all my bills and bank balance"

    # Interactive mode
    python mimic.py

    # Run individual skills directly
    python mimic.py play skills/private/bank-login.json
    python mimic.py play skills/private/scrape.json --extract

    # List available skills
    python mimic.py skills
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from skills_player.config import LLM_MODEL, LLM_PROVIDER, SKILLS_DIR
from skills_player.player import get_llm, play_skill
from skills_player.skills import list_skills as get_skills_list


# Directories
PUBLIC_SKILLS = SKILLS_DIR / "public"
PRIVATE_SKILLS = SKILLS_DIR / "private"


def load_skills_manifest() -> dict[str, dict]:
    """Load all available skills and their metadata."""
    skills = {}

    for skills_dir in [PUBLIC_SKILLS, PRIVATE_SKILLS]:
        if not skills_dir.exists():
            continue

        for file in skills_dir.glob("*.json"):
            try:
                with open(file) as f:
                    skill = json.load(f)
                    name = file.stem
                    skills[name] = {
                        "name": name,
                        "title": skill.get("title", name),
                        "description": skill.get("description", ""),
                        "env_vars": list(skill.get("env_vars", {}).keys()),
                        "extract_prompt": skill.get("extract_prompt"),
                        "task_prompt": skill.get("task_prompt"),
                        "path": str(file),
                        "is_private": skills_dir == PRIVATE_SKILLS,
                    }
            except (json.JSONDecodeError, OSError):
                pass

    return skills


def build_planning_prompt(user_request: str, skills: dict[str, dict]) -> str:
    """
    Build the planning prompt for the LLM orchestrator.

    The LLM analyzes the user's request and decides which skills to run.
    """
    skills_info = []
    for name, info in skills.items():
        skills_info.append(
            f"  - {name}: {info['title']}\n"
            f"    Description: {info['description']}"
        )
    skills_text = "\n".join(skills_info)

    return f"""You are Mimic, an intelligent browser automation orchestrator.

Your job is to analyze the user's request and decide which skills to run.

AVAILABLE SKILLS:
{skills_text}

USER REQUEST:
"{user_request}"

INSTRUCTIONS:
Analyze the user's request and determine:
1. Which skills are needed to fulfill this request
2. The order in which they should run
3. Whether data needs to be passed between skills

IMPORTANT RULES:
- Only include skills that are actually needed for this specific request
- If the user says "only" or specifies a single action, respect that
- DO NOT add extra skills unless the user explicitly asks for them
- For shopping workflows: getting a list is separate from adding to cart
- DO NOT checkout or make payments unless explicitly asked

Respond with ONLY a JSON object in this exact format:
{{
    "reasoning": "Brief explanation of your decision",
    "skills_to_run": ["skill-name-1", "skill-name-2"],
    "pass_data": true
}}

The "skills_to_run" array should contain skill names from the AVAILABLE SKILLS list.
Set "pass_data" to true if later skills need data from earlier ones.

JSON response:"""


async def ask_llm_for_plan(
    user_request: str,
    skills: dict[str, dict],
) -> dict[str, Any]:
    """
    Ask the LLM to create an execution plan based on the user's request.

    Returns:
        Plan dictionary with reasoning, skills_to_run, and pass_data
    """
    prompt = build_planning_prompt(user_request, skills)

    print("🧠 Analyzing your request...")

    try:
        from typing import Any

        llm = get_llm()

        # Handle different LLM types - ChatOpenRouter vs LangChain
        response: Any
        response_text: str

        # Check if it's a browser-use ChatOpenRouter
        if hasattr(llm, 'provider') and getattr(llm, 'provider', None) == 'openrouter':
            # Use browser_use message types for ChatOpenRouter
            from browser_use.llm.messages import UserMessage

            messages_browser_use: list[Any] = [UserMessage(content=prompt)]
            response = await llm.ainvoke(messages_browser_use)  # type: ignore

            # ChatInvokeCompletion[str] has a 'completion' attribute
            if hasattr(response, 'completion'):
                completion = response.completion
                response_text = completion if isinstance(completion, str) else str(completion)
            else:
                response_text = str(response)
        else:
            # Use LangChain message types for other providers
            from langchain_core.messages import HumanMessage

            messages_langchain: list[Any] = [HumanMessage(content=prompt)]
            response = await llm.ainvoke(messages_langchain)  # type: ignore

            # LangChain AIMessage has a 'content' attribute
            if hasattr(response, 'content'):
                content = response.content
                response_text = content if isinstance(content, str) else str(content)
            else:
                response_text = str(response)

        # Parse JSON from response
        try:
            plan = json.loads(response_text.strip())
        except json.JSONDecodeError:
            # Find JSON object in the response
            start = response_text.find('{')
            if start == -1:
                raise json.JSONDecodeError("No JSON found", response_text, 0)

            # Find matching closing brace
            depth = 0
            end = start
            for i, char in enumerate(response_text[start:], start):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            json_str = response_text[start:end]
            plan = json.loads(json_str)

        return plan

    except json.JSONDecodeError as e:
        print(f"⚠️  Could not parse LLM response as JSON: {e}")
        return {
            "reasoning": "Failed to parse LLM response",
            "skills_to_run": [],
            "pass_data": False,
            "error": str(e),
        }
    except Exception as e:
        print(f"⚠️  LLM error: {e}")
        return {
            "reasoning": f"LLM error: {e}",
            "skills_to_run": [],
            "pass_data": False,
            "error": str(e),
        }


async def run_skill_with_context(
    skill_name: str,
    skills: dict[str, dict],
    context: dict | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """
    Run a single skill with optional context from previous skills.

    Args:
        skill_name: Name of the skill to run
        skills: Skills manifest
        context: Data from previous skill runs
        headless: Run browser headless

    Returns:
        Result dictionary with extracted data
    """
    if skill_name not in skills:
        return {"success": False, "error": f"Skill not found: {skill_name}"}

    skill_info = skills[skill_name]
    skill_path = skill_info["path"]

    print(f"\n{'='*60}")
    print(f"🎯 Running: {skill_info['title']}")
    print("=" * 60)

    # Build context-aware prompt if we have context
    extract_prompt = skill_info.get("extract_prompt")
    if context and skill_info.get("task_prompt"):
        task_prompt = skill_info["task_prompt"]
        if "shopping_list" in context:
            items = context["shopping_list"]
            if isinstance(items, list):
                items_json = json.dumps([
                    item.get("item_name", item) if isinstance(item, dict) else item
                    for item in items
                ])
                extract_prompt = f"SHOPPING LIST: {items_json}\n\n{task_prompt}"

    try:
        result = await play_skill(
            skill_path=skill_path,
            headless=headless,
            do_extract=True,
            extract_prompt=extract_prompt,
            interactive=True,
            loose_mode=True,
            verbose=False,  # Quiet mode by default for orchestrator
        )

        # Check if we have a result (even if success is False, agent may have extracted data)
        result_text = result.get("result", "")
        
        if result_text:
            # Parse JSON from result
            try:
                if isinstance(result_text, dict):
                    return {"success": True, "data": result_text}
                elif "{" in str(result_text):
                    json_start = str(result_text).index("{")
                    json_end = str(result_text).rindex("}") + 1
                    data = json.loads(str(result_text)[json_start:json_end])
                    return {"success": True, "data": data}
                else:
                    return {"success": True, "data": {"raw": result_text}}
            except (json.JSONDecodeError, ValueError):
                return {"success": True, "data": {"raw": result_text}}

        # No result text at all
        if result.get("success"):
            return {"success": True, "data": {}}
        
        return {"success": False, "error": result.get("error", "Skill did not return data")}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def orchestrate(
    user_request: str,
    headless: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Main orchestration function - uses LLM to decide what to run.

    Args:
        user_request: Natural language description of what to do
        headless: Run browsers headless
        dry_run: Preview without executing

    Returns:
        Summary of execution
    """
    skills = load_skills_manifest()

    print("\n" + "=" * 60)
    print("🤖 MIMIC ORCHESTRATOR")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"LLM: {LLM_PROVIDER}/{LLM_MODEL}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    print(f"📝 Request: {user_request}")
    print()

    # Ask LLM to create the plan
    plan = await ask_llm_for_plan(user_request, skills)

    if plan.get("error"):
        print(f"\n❌ Planning failed: {plan.get('reasoning')}")
        return {"success": False, "error": plan.get("error")}

    skills_to_run = plan.get("skills_to_run", [])
    reasoning = plan.get("reasoning", "No reasoning provided")
    pass_data = plan.get("pass_data", False)

    print(f"\n💭 AI Decision: {reasoning}")
    print(f"\n🔧 Skills to execute: {len(skills_to_run)}")
    for i, skill in enumerate(skills_to_run, 1):
        skill_info = skills.get(skill, {})
        print(f"   {i}. {skill_info.get('title', skill)}")

    if not skills_to_run:
        print("\n⚠️  No skills selected for this request.")
        return {"success": False, "error": "No skills matched the request"}

    if dry_run:
        print("\n[DRY RUN] Would execute the above skills in order")
        return {
            "dry_run": True,
            "plan": plan,
            "skills": skills_to_run,
        }

    # Execute skills in order, passing context if needed
    context: dict[str, Any] = {}
    results: list[dict] = []

    for skill_name in skills_to_run:
        result = await run_skill_with_context(
            skill_name=skill_name,
            skills=skills,
            context=context if pass_data else None,
            headless=headless,
        )

        results.append({
            "skill": skill_name,
            "result": result,
        })

        # Update context with result data for next skill
        if pass_data and result.get("success") and result.get("data"):
            data = result["data"]
            if "shopping_list" in data:
                context["shopping_list"] = data["shopping_list"]
            if "orders" in data:
                context["orders"] = data["orders"]
            if "items_added" in data:
                context["items_added"] = data["items_added"]
            if "balance" in data or "checking_balance" in data:
                context["balance"] = data.get("balance") or data.get("checking_balance")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 EXECUTION SUMMARY")
    print("=" * 60)

    successful = sum(1 for r in results if r["result"].get("success"))
    print(f"✅ Completed: {successful}/{len(results)} skills")

    for r in results:
        skill = r["skill"]
        status = "✅" if r["result"].get("success") else "❌"
        print(f"   {status} {skill}")
        if r["result"].get("error"):
            print(f"      Error: {r['result']['error']}")

    return {
        "success": successful == len(results),
        "plan": plan,
        "results": results,
        "context": context,
    }


async def interactive_mode(headless: bool = False) -> None:
    """Run in interactive mode, prompting for input."""
    print("\n" + "=" * 60)
    print("🤖 MIMIC - Natural Language Browser Automation")
    print("=" * 60)
    print()
    print("Tell me what you want to do in plain English.")
    print("The AI will figure out which skills to run.")
    print()
    print("Examples:")
    print('  • "Get my Alexa shopping list"')
    print('  • "Get my shopping list and add items to Walmart cart"')
    print('  • "Check all my bills and bank balance"')
    print('  • "Show me my recent Amazon orders"')
    print()

    try:
        prompt = input("📝 What would you like to do?\n> ").strip()

        if not prompt:
            print("No prompt provided")
            return

        await orchestrate(user_request=prompt, headless=headless)

    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
    except EOFError:
        print("\nNo input received")


# =============================================================================
# SKILL COMMANDS
# =============================================================================

def list_skills_command() -> None:
    """Display all available skills."""
    skills = get_skills_list()

    if not skills:
        print(f"\n📭 No skills found in {SKILLS_DIR}/")
        print("\nCreate one:")
        print("  1. Open Chrome DevTools (F12)")
        print("  2. Go to Recorder tab")
        print("  3. Create and export as JSON")
        return

    print(f"\n📁 Skills ({len(skills)}):")
    print(f"   LLM: {LLM_PROVIDER}/{LLM_MODEL}")
    print("-" * 60)

    for skill in skills:
        env_vars = skill['env_vars']
        env_note = f" [needs: {', '.join(env_vars)}]" if env_vars else ""
        extract_note = " 📊" if skill['has_extract'] else ""
        steps = skill['steps']
        print(f"  {skill['file']}: {skill['title']} ({steps} steps){env_note}{extract_note}")
        if skill['description']:
            print(f"    └─ {skill['description'][:60]}...")

    print()


async def play_skill_command(
    skill_path: str,
    headless: bool = False,
    do_extract: bool = False,
    extract_prompt: str | None = None,
    interactive: bool = True,
    loose_mode: bool = False,
) -> dict[str, Any]:
    """Play an individual skill."""
    return await play_skill(
        skill_path=skill_path,
        headless=headless,
        do_extract=do_extract,
        extract_prompt=extract_prompt,
        interactive=interactive,
        loose_mode=loose_mode,
    )


# =============================================================================
# MAIN CLI
# =============================================================================

def main() -> None:
    """CLI entry point."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "skills":
            list_skills_command()
            return

        if cmd == "play":
            _handle_play_command()
            return

    _handle_orchestrate_command()


def _handle_play_command() -> None:
    """Handle the 'play' subcommand for individual skills."""
    parser = argparse.ArgumentParser(
        prog="mimic.py play",
        description="Play an individual skill"
    )
    parser.add_argument("skill", help="Path to the skill JSON file")
    parser.add_argument("--extract", "-x", action="store_true",
                        help="Use the skill's built-in extract_prompt")
    parser.add_argument("--extract-prompt", "-p",
                        help="Custom extraction prompt")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser without UI")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Disable interactive MFA/user input prompts")
    parser.add_argument("--loose", "-l", action="store_true",
                        help="Enable loose mode: agent adapts to page changes")

    args = parser.parse_args(sys.argv[2:])

    try:
        result = asyncio.run(play_skill_command(
            skill_path=args.skill,
            headless=args.headless,
            do_extract=args.extract,
            extract_prompt=args.extract_prompt,
            interactive=not args.no_interactive,
            loose_mode=args.loose,
        ))
        sys.exit(0 if result.get("success") else 1)

    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _handle_orchestrate_command() -> None:
    """Handle natural language prompts - the main AI orchestration mode."""
    parser = argparse.ArgumentParser(
        description="Mimic - Browser Automation with Muscle Memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Natural language - AI decides what to run
  python mimic.py                                    # Interactive mode
  python mimic.py "Get my Alexa shopping list"
  python mimic.py "Get my Alexa list and add to Walmart cart"
  python mimic.py --dry-run "Check all my bills"

  # Run individual skills directly
  python mimic.py play skills/private/bank-login.json
  python mimic.py play skills/private/scrape.json --extract

  # List available skills
  python mimic.py skills

Environment Variables:
  LLM_PROVIDER    LLM provider: openrouter, openai, anthropic
  LLM_MODEL       Model name (default: google/gemini-2.5-flash)
        """
    )

    parser.add_argument("prompt", nargs="*",
                        help="Natural language request")
    parser.add_argument("--headless", action="store_true",
                        help="Run browsers without UI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would run without executing")

    args = parser.parse_args()

    try:
        if args.prompt:
            prompt = " ".join(args.prompt)
            asyncio.run(orchestrate(
                user_request=prompt,
                headless=args.headless,
                dry_run=args.dry_run,
            ))
            return

        asyncio.run(interactive_mode(headless=args.headless))

    except KeyboardInterrupt:
        print("\n\n⛔ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
