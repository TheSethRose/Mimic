"""Command-line interface for the skills player."""

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from .config import LLM_MODEL, LLM_PROVIDER, SKILLS_DIR
from .player import play_skill
from .skills import list_skills

load_dotenv()


def main() -> None:
    """Main entry point for the skills player CLI."""
    parser = argparse.ArgumentParser(
        description="Mimic - Turn Chrome Recordings into Unbreakable AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py list
  python main.py play skills/bills/example.json
  python main.py play skills/login.json --loose
  python main.py play skills/scrape.json --extract
  python main.py play skills/form.json --extract-prompt "Get the confirmation number"
  python main.py play skills/check.json --headless

Environment Variables:
  LLM_PROVIDER    LLM provider: openrouter, openai, anthropic (default: openrouter)
  LLM_MODEL       Model name (default: google/gemini-2.5-flash)

Creating skills:
  1. Open Chrome DevTools (F12)
  2. Click ⋮ → More tools → Recorder
  3. Click "Create a new recording"
  4. Perform your actions
  5. Export as JSON
  6. Replace sensitive values with {{ENV_VAR}} placeholders
  7. Add to .env: ENV_VAR=actual_value
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    subparsers.add_parser("list", help="List available skills")

    # Play command
    play_parser = subparsers.add_parser("play", help="Play a skill")
    play_parser.add_argument(
        "skill",
        help="Path to the skill JSON file"
    )
    play_parser.add_argument(
        "--extract", "-x",
        action="store_true",
        help="Use the skill's built-in extract_prompt"
    )
    play_parser.add_argument(
        "--extract-prompt", "-p",
        help="Custom extraction prompt (overrides built-in)"
    )
    play_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without UI"
    )
    play_parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive MFA/user input prompts"
    )
    play_parser.add_argument(
        "--loose", "-l",
        action="store_true",
        help="Enable loose mode: agent adapts to page changes instead of following steps strictly"
    )
    play_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed step-by-step logging from browser-use"
    )

    args = parser.parse_args()

    if args.command == "list":
        _handle_list()

    elif args.command == "play":
        _handle_play(args)

    else:
        parser.print_help()


def _handle_list() -> None:
    """Handle the list command."""
    skills = list_skills()
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
            print(f"    └─ {skill['description'][:50]}...")
    print()


def _handle_play(args: argparse.Namespace) -> None:
    """Handle the play command."""
    try:
        result = asyncio.run(play_skill(
            skill_path=args.skill,
            headless=args.headless,
            do_extract=args.extract,
            extract_prompt=args.extract_prompt,
            interactive=not args.no_interactive,
            loose_mode=args.loose,
            verbose=args.verbose,
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


if __name__ == "__main__":
    main()
