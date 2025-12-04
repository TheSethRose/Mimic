"""Main skill player orchestration."""

import os
from typing import Any, TYPE_CHECKING

from .config import LLM_MODEL, LLM_PROVIDER
from .skills import (
    check_required_env_vars,
    load_skill,
    skill_to_task,
    substitute_env_vars,
)

if TYPE_CHECKING:
    from browser_use import Agent, Browser


def get_llm():
    """
    Initialize the LLM for the agent.

    Configurable via environment variables:
        - LLM_PROVIDER: "openrouter" (default), "openai", "anthropic"
        - LLM_MODEL: Model name (default: "google/gemini-2.5-flash")

    Returns:
        Configured LLM instance.

    Raises:
        ValueError: If required API key is not set.
    """
    if LLM_PROVIDER == "openrouter":
        from browser_use.llm.openrouter.chat import ChatOpenRouter

        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key is None:
            raise ValueError("OPENROUTER_API_KEY is not set in .env file")

        return ChatOpenRouter(
            model=LLM_MODEL,
            api_key=api_key,
        )

    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if api_key is None:
            raise ValueError("OPENAI_API_KEY is not set in .env file")

        return ChatOpenAI(
            model=LLM_MODEL,
            api_key=api_key,
        )

    elif LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key is None:
            raise ValueError("ANTHROPIC_API_KEY is not set in .env file")

        return ChatAnthropic(
            model=LLM_MODEL,
            api_key=api_key,
        )

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


MFA_INSTRUCTION = """

IMPORTANT - VERIFICATION & MFA HANDLING:
If you encounter ANY of the following, use the 'ask_user_for_input' tool:
- A page asking HOW to receive a verification code
- A page with a field to enter a verification/OTP code
- Security questions or identity verification prompts
- CAPTCHA challenges
- Any choice or input you're unsure about

When using 'ask_user_for_input':
- In 'what_i_see': List ALL buttons, options, and fields visible
- In 'what_i_need': Ask the user what to click/select OR what code to enter

Do NOT assume what the user wants - always ask first!"""

LOOSE_MODE_INSTRUCTION = """

FLEXIBLE EXECUTION MODE:
You are operating in loose/adaptive mode. The steps provided are HINTS, not strict commands.
- If an element can't be found exactly as described, look for similar elements
- Use your visual understanding and reasoning to complete the goal
- Adapt to page layout changes - the recording may be outdated
- Focus on completing the GOAL, not following steps literally"""


async def play_skill(
    skill_path: str,
    headless: bool = False,
    do_extract: bool = False,
    extract_prompt: str | None = None,
    interactive: bool = True,
    loose_mode: bool = False,
) -> dict[str, Any]:
    """
    Play a browser automation skill using browser-use.

    Args:
        skill_path: Path to the skill JSON file.
        headless: Run browser in headless mode.
        do_extract: Use the skill's built-in extract_prompt.
        extract_prompt: Custom extraction prompt (overrides built-in).
        interactive: Enable interactive mode for MFA/user input prompts.
        loose_mode: Enable loose/adaptive mode - agent reasons more freely.

    Returns:
        Dict with success status, result, errors, and steps completed.
    """
    skill = load_skill(skill_path)
    title = skill.get("title", "Skill")

    print(f"\n▶️  Playing: {title}")
    if skill.get("description"):
        print(f"   {skill['description']}")
    print("-" * 50)

    # Check for missing env vars
    missing = check_required_env_vars(skill)
    if missing:
        print("❌ Missing environment variables:")
        for var in missing:
            desc = skill.get("env_vars", {}).get(var, "Required")
            print(f"   {var}: {desc}")
        print("\nAdd these to your .env file and try again.")
        return {"success": False, "error": "Missing environment variables"}

    # Substitute environment variables
    try:
        skill = substitute_env_vars(skill)
        print("🔐 Credentials loaded from environment")
    except ValueError as e:
        print(f"❌ {e}")
        return {"success": False, "error": str(e)}

    # Convert to task
    # Note: We use mask_passwords=True even for execution to avoid sending
    # plaintext credentials to the LLM API. The agent will use the input
    # tool to handle sensitive fields.
    task = skill_to_task(skill, mask_passwords=True, loose_mode=loose_mode)
    task_display = task  # Same now since we always mask

    # Determine extraction prompt
    if extract_prompt is not None:
        final_extract: str | None = extract_prompt
    elif do_extract:
        final_extract = skill.get("extract_prompt")
    else:
        final_extract = None

    if final_extract:
        task += f"\n\nAfter completing all steps, {final_extract}"
        task_display += f"\n\nAfter completing all steps, {final_extract}"
        print(f"📊 Will extract: {final_extract[:60]}...")

    # Add mode-specific instructions
    if loose_mode:
        task += LOOSE_MODE_INSTRUCTION
        print("🔓 Loose mode: Agent will adapt to page changes")

    # Add MFA instruction if interactive mode is enabled
    if interactive:
        task += MFA_INSTRUCTION
        print("🔐 Interactive mode: Will prompt for MFA/verification if needed")

    print(f"\n📝 Generated {task_display.count(chr(10))} task lines")
    print(f"🧠 LLM: {LLM_PROVIDER}/{LLM_MODEL}")

    # Import browser_use components (lazy import for faster CLI startup)
    from browser_use import Agent, Browser
    from .tools import create_interactive_tools

    # Initialize
    llm = get_llm()
    browser = Browser(headless=headless)

    # Create tools with interactive capabilities
    tools = create_interactive_tools() if interactive else None

    print(f"🌐 Browser: {'headless' if headless else 'visible'}")
    print("🚀 Starting agent...\n")

    try:
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            tools=tools,
        )

        history = await agent.run()

        # Results
        print("\n" + "=" * 50)

        success = history.is_successful()
        if success:
            print("✅ Completed successfully!")
        else:
            print("⚠️ Completed with issues")

        # Show result
        final_result = history.final_result()
        if final_result:
            print(f"\n📋 Result:\n{final_result}")

        # Show errors
        errors = [e for e in history.errors() if e]
        if errors:
            print("\n⚠️ Errors encountered:")
            for err in errors[:5]:  # Limit to 5
                print(f"   - {err[:100]}")

        return {
            "success": success,
            "result": final_result,
            "errors": errors,
            "steps_completed": history.number_of_steps(),
        }

    finally:
        await browser.stop()
        print("\n🧹 Browser closed.")
