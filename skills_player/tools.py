"""Interactive tools for agent-user communication."""

from typing import TYPE_CHECKING

from .preferences import load_preferences, normalize_prompt_key, save_preferences

if TYPE_CHECKING:
    from browser_use import ActionResult, Tools


def create_interactive_tools(include_finance: bool = True) -> "Tools":
    """
    Create tools that allow the agent to ask the user for input.

    This is useful for MFA codes, CAPTCHAs, security questions, etc.

    Args:
        include_finance: If True, include finance/banking tools.

    Returns:
        Tools instance with interactive actions registered.
    """
    # Import here to avoid circular imports and allow type checking
    from browser_use import ActionResult, Tools

    tools = Tools()

    @tools.action(
        description="""Ask the user for input or guidance when you encounter
        a verification page, MFA prompt, security question, CAPTCHA, or any
        situation requiring human decision/input.

        Use this when you see:
        - Pages asking HOW to send a verification code
        - One-time password (OTP) / verification code entry fields
        - SMS/Email verification code prompts
        - Security questions
        - CAPTCHA challenges
        - "Verify your identity" pages
        - Multiple choice options you're unsure about
        - Any form asking for information you don't have

        IMPORTANT: Describe EXACTLY what you see on the page, including all
        buttons and options. Don't assume what the user wants."""
    )
    def ask_user_for_input(
        what_i_see: str,
        what_i_need: str,
    ) -> ActionResult:
        """
        Ask the user for input or a decision interactively.

        Args:
            what_i_see: Describe what's on the page (buttons, fields, options)
            what_i_need: What input or decision you need from the user

        Returns:
            ActionResult with the user's response or error.
        """
        # Check if we have a saved preference for this type of prompt
        pref_key, is_saveable = normalize_prompt_key(what_i_see, what_i_need)

        if is_saveable and pref_key:
            preferences = load_preferences()
            if pref_key in preferences:
                saved_response = preferences[pref_key]
                print("\n" + "=" * 60)
                print("🔄 USING SAVED PREFERENCE")
                print("=" * 60)
                print(f"\n📄 What I see on the page:\n   {what_i_see[:200]}...")
                print(f"\n✅ Auto-applying saved preference: {saved_response}")
                print("   (Delete skills/.preferences.json to reset)")
                print()
                return ActionResult(
                    extracted_content=f"User preference (saved): {saved_response}",
                    include_in_memory=True
                )

        print("\n" + "=" * 60)
        print("🔐 USER INPUT REQUIRED")
        print("=" * 60)
        print(f"\n📄 What I see on the page:\n   {what_i_see}")
        print(f"\n❓ {what_i_need}")
        print()

        try:
            user_input = input("👤 Your response: ").strip()
            if user_input:
                # Mask the display but return actual value
                display_len = min(len(user_input), 20)
                if len(user_input) > 3:
                    masked = user_input[:3] + '*' * (display_len - 3)
                else:
                    masked = user_input
                print(f"✅ Received: {masked}")

                # Save preference if this is a saveable choice
                if is_saveable and pref_key:
                    preferences = load_preferences()
                    preferences[pref_key] = user_input
                    save_preferences(preferences)
                    print(f"💾 Saved preference for future use (key: {pref_key})")

                return ActionResult(
                    extracted_content=f"User responded: {user_input}",
                    include_in_memory=True
                )
            return ActionResult(
                error="User provided empty input",
                include_in_memory=True
            )
        except EOFError:
            return ActionResult(
                error="No input available (non-interactive mode)",
                include_in_memory=True
            )
        except KeyboardInterrupt:
            return ActionResult(
                error="User cancelled input",
                include_in_memory=True
            )

    @tools.action(
        description="""Notify the user about something important and wait for
        acknowledgment. Use when the user needs to complete an action manually,
        when waiting for an external process, or when a verification code was
        just sent and you're waiting for the user to receive it."""
    )
    def notify_and_wait(
        message: str,
        wait_prompt: str = "Press Enter when ready to continue...",
    ) -> ActionResult:
        """
        Show a message and wait for user acknowledgment.

        Args:
            message: The message to display to the user.
            wait_prompt: What to show while waiting.

        Returns:
            ActionResult indicating user acknowledged or error.
        """
        print("\n" + "=" * 60)
        print("📢 NOTIFICATION")
        print("=" * 60)
        print(f"\n{message}")
        print()

        try:
            input(f"⏳ {wait_prompt}")
            return ActionResult(
                extracted_content="User acknowledged and is ready to continue",
                include_in_memory=True
            )
        except (EOFError, KeyboardInterrupt):
            return ActionResult(
                error="User did not acknowledge",
                include_in_memory=True
            )

    # Register optional tool sets
    if include_finance:
        from .custom_tools import register_finance_tools
        register_finance_tools(tools)

    return tools
