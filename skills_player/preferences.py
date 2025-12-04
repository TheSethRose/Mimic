"""User preference storage for MFA choices and other settings."""

import json
from typing import Any

from .config import PREFERENCES_FILE


def load_preferences() -> dict[str, str]:
    """
    Load saved user preferences from file.

    Returns:
        Dictionary of preference keys to saved values.
    """
    if PREFERENCES_FILE.exists():
        try:
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_preferences(preferences: dict[str, str]) -> None:
    """
    Save user preferences to file.

    Args:
        preferences: Dictionary of preference keys to values.
    """
    try:
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2)
    except OSError as e:
        print(f"⚠️ Could not save preferences: {e}")


def normalize_prompt_key(what_i_see: str, what_i_need: str) -> tuple[str, bool]:
    """
    Create a normalized key from the page description for matching preferences.

    Args:
        what_i_see: Description of what's visible on the page.
        what_i_need: Description of what input is needed from user.

    Returns:
        Tuple of (key, is_saveable) where is_saveable is False for one-time
        codes like OTPs.
    """
    text = (what_i_see + " " + what_i_need).lower()

    # Check if asking for a one-time code (should NOT be saved)
    otp_phrases = [
        'provide the verification code', 'enter the code', 'provide the code',
        'input the code', 'type the code', 'what is the code',
        '6-digit code', '6 digit code', 'enter otp', 'input otp',
        'code that was sent', 'code sent to your'
    ]
    is_otp_request = any(phrase in text for phrase in otp_phrases)

    # Check if this is asking for a CAPTCHA (should NOT be saved)
    is_captcha = 'captcha' in text

    if is_otp_request or is_captcha:
        return ("", False)

    # Extract key phrases that identify the type of prompt
    identifiers: list[str] = []

    # Look for site/service identifiers
    sites = [
        'kia', 'pnc', 'grayson', 'anna', 'smarthub',
        'municipal', 'hyundai', 'chase', 'wells fargo'
    ]
    for site in sites:
        if site in text:
            identifiers.append(site)

    # Look for verification method choice (saveable)
    method_options = [
        'email', 'text message', 'sms', 'voice message', 'call me'
    ]
    preference_phrases = [
        'which method', 'how to receive', 'preferred contact',
        'select your preferred', 'how would you like', 'choose',
        'radio button', 'contact method'
    ]
    has_method_options = any(m in text for m in method_options)
    is_asking_preference = any(p in text for p in preference_phrases)

    if has_method_options and is_asking_preference:
        identifiers.append('mfa_method')

    # Look for trust/remember device (saveable)
    trust_phrases = ['trust', 'remember', '180 days', '30 days']
    if any(phrase in text for phrase in trust_phrases):
        identifiers.append('trust_device')

    # Look for terms acceptance (saveable)
    if 'terms' in text and 'conditions' in text:
        identifiers.append('terms')

    # Only return key if we found saveable identifiers
    saveable_choices = {'mfa_method', 'trust_device', 'terms'}
    if identifiers and any(i in saveable_choices for i in identifiers):
        return ('_'.join(sorted(set(identifiers))), True)

    return ("", False)
