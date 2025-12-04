"""Interactive tools for agent-user communication."""

import json
import re
from typing import TYPE_CHECKING

from .preferences import load_preferences, normalize_prompt_key, save_preferences

if TYPE_CHECKING:
    from browser_use import ActionResult, Tools
    from browser_use.browser.session import BrowserSession


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
    from browser_use.browser.session import BrowserSession

    tools = Tools()

    @tools.action(
        description="""Parse JSON data from the current page. Use this when the
        page displays raw JSON (like an API response). Optionally filter the
        results using a simple condition.

        Examples:
        - parse_page_json() - returns all JSON data
        - parse_page_json(array_key="items") - extracts the "items" array
        - parse_page_json(array_key="items", filter_key="completed", filter_value=False)
          - extracts items where completed=false
        - parse_page_json(array_key="listItems", filter_key="completed", filter_value=False, extract_fields=["value"])
          - extracts just the "value" field from non-completed items"""
    )
    async def parse_page_json(
        browser_session: BrowserSession,
        array_key: str = "",
        filter_key: str = "",
        filter_value: str | bool | None = None,
        extract_fields: list[str] | None = None,
    ) -> ActionResult:
        """
        Parse JSON from the current page content.

        Args:
            browser_session: Browser session (injected automatically)
            array_key: Key to extract an array from (e.g., "items", "listItems")
            filter_key: Field to filter on (e.g., "completed", "status")
            filter_value: Value to match for filter (e.g., False, "active")
            extract_fields: List of fields to extract from each item

        Returns:
            ActionResult with parsed JSON data.
        """
        try:
            # Get the page and use JavaScript to get the body text
            page = await browser_session.get_current_page()
            if not page:
                return ActionResult(
                    error="No page available",
                    include_in_memory=True
                )

            # Get page content via JavaScript - works for raw JSON pages
            # browser-use requires arrow function format for evaluate()
            content = await page.evaluate("() => document.body.innerText || document.body.textContent || ''")

            if not content or not content.strip():
                # Try getting the full HTML if innerText is empty
                content = await page.evaluate("() => document.documentElement.outerHTML || ''")

            json_text = content.strip()

            # Clean up HTML entities
            json_text = json_text.replace('&quot;', '"')
            json_text = json_text.replace('&amp;', '&')
            json_text = json_text.replace('&lt;', '<')
            json_text = json_text.replace('&gt;', '>')
            json_text = json_text.strip()

            # Parse the JSON
            data = json.loads(json_text)

            # Extract array if specified - search recursively if not at root
            if array_key:
                found_data = None
                
                # First check root level
                if isinstance(data, dict) and array_key in data:
                    found_data = data[array_key]
                else:
                    # Search one level deep (common pattern: {"dynamicKey": {"listItems": [...]}})
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, dict) and array_key in value:
                                found_data = value[array_key]
                                break
                
                if found_data is not None:
                    data = found_data
                else:
                    return ActionResult(
                        error=f"Key '{array_key}' not found in JSON (checked root and one level deep)",
                        include_in_memory=True
                    )

            # Filter if specified
            if filter_key and isinstance(data, list):
                filtered = []
                for item in data:
                    if isinstance(item, dict):
                        item_value = item.get(filter_key)
                        # Handle boolean comparison
                        if filter_value is False:
                            if item_value is False or item_value is None:
                                filtered.append(item)
                        elif filter_value is True:
                            if item_value is True:
                                filtered.append(item)
                        elif item_value == filter_value:
                            filtered.append(item)
                data = filtered

            # Extract specific fields if specified
            if extract_fields and isinstance(data, list):
                extracted = []
                for item in data:
                    if isinstance(item, dict):
                        if len(extract_fields) == 1:
                            # Single field - just get the value
                            val = item.get(extract_fields[0])
                            if val is not None:
                                extracted.append(val)
                        else:
                            # Multiple fields - create a dict
                            extracted.append({
                                field: item.get(field)
                                for field in extract_fields
                                if field in item
                            })
                data = extracted

            result_json = json.dumps(data, indent=2)
            item_count = len(data) if isinstance(data, list) else 1

            print(f"\n📋 Parsed JSON: {item_count} items")

            return ActionResult(
                extracted_content=result_json,
                include_in_memory=True
            )

        except json.JSONDecodeError as e:
            return ActionResult(
                error=f"Failed to parse JSON: {e}",
                include_in_memory=True
            )
        except Exception as e:
            return ActionResult(
                error=f"Error parsing page: {e}",
                include_in_memory=True
            )

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
