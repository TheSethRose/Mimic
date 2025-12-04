"""
Automation suite for file organization, data integration, and security.

This module provides three main tools:
- FileOrganizer: Auto-filer for downloaded documents
- Ledger: Data integrator for financial tracking (CSV/JSONL)
- SecuritySuite: TOTP generation and stealth browser configuration
"""

import csv
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# Try to import pyotp, handle if missing
try:
    import pyotp
except ImportError:
    pyotp = None

if TYPE_CHECKING:
    from browser_use import ActionResult


class FileOrganizer:
    """
    Organizes downloaded files based on extracted metadata.

    Automatically categorizes and renames files using a consistent
    naming convention: YYYY-MM-DD_ServiceName_$Amount.ext
    """

    # Category keywords for auto-classification
    CATEGORY_KEYWORDS = {
        "Utilities": [
            "water", "electric", "gas", "internet", "phone",
            "cable", "power", "utility", "sewage", "trash"
        ],
        "Financial": [
            "bank", "finance", "card", "credit", "loan",
            "mortgage", "insurance", "investment"
        ],
        "Retail": [
            "amazon", "walmart", "target", "costco", "sams",
            "bestbuy", "home depot", "lowes"
        ],
        "Healthcare": [
            "medical", "doctor", "hospital", "pharmacy",
            "dental", "vision", "health"
        ],
        "Subscriptions": [
            "netflix", "spotify", "hulu", "disney", "youtube",
            "adobe", "microsoft", "apple"
        ],
    }

    def __init__(self, base_dir: str = "~/Drive/Bills"):
        """
        Initialize the FileOrganizer.

        Args:
            base_dir: Base directory for organized files.
                      Supports ~ expansion.
        """
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _determine_category(self, service_name: str) -> str:
        """
        Determine the category based on service name keywords.

        Args:
            service_name: Name of the service/vendor.

        Returns:
            Category string.
        """
        service_lower = service_name.lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in service_lower for kw in keywords):
                return category

        return "General"

    def organize(
        self,
        source_path: str,
        metadata: dict,
    ) -> str:
        """
        Rename and move a file based on metadata.

        Args:
            source_path: Path to the source file.
            metadata: Dict with keys:
                - service_name: Name of the service (required)
                - date: Date string YYYY-MM-DD (optional)
                - amount: Dollar amount (optional)
                - category: Override auto-detection (optional)

        Returns:
            Success message with new path, or error message.
        """
        if not os.path.exists(source_path):
            return f"Error: Source file {source_path} not found."

        # Extract and sanitize metadata
        service = metadata.get("service_name", "UnknownService")
        service = service.replace(" ", "").replace("/", "-")

        date_str = metadata.get("date", datetime.now().strftime("%Y-%m-%d"))

        amount = str(metadata.get("amount", "0.00"))
        amount = amount.replace("$", "").replace(",", "")

        # Determine category
        category = metadata.get("category") or self._determine_category(service)

        target_dir = self.base_dir / category
        target_dir.mkdir(exist_ok=True)

        # Create new filename: YYYY-MM-DD_Service_$Amount.ext
        extension = Path(source_path).suffix
        new_filename = f"{date_str}_{service}_${amount}{extension}"
        target_path = target_dir / new_filename

        # Handle duplicates
        counter = 1
        while target_path.exists():
            new_filename = f"{date_str}_{service}_${amount}_{counter}{extension}"
            target_path = target_dir / new_filename
            counter += 1

        try:
            shutil.move(source_path, target_path)
            return f"Successfully moved to {target_path}"
        except OSError as e:
            return f"Failed to move file: {e}"


class Ledger:
    """
    Appends extracted data to a local 'database' (CSV).

    Acts as the integration tool for tracking financial data
    across multiple skills and sources.
    """

    DEFAULT_HEADERS = [
        "date",
        "service",
        "amount",
        "due_date",
        "category",
        "notes",
        "source_skill",
    ]

    def __init__(self, ledger_path: str = "finance_ledger.csv"):
        """
        Initialize the Ledger.

        Args:
            ledger_path: Path to the CSV ledger file.
        """
        self.ledger_path = Path(ledger_path)
        self.headers = self.DEFAULT_HEADERS

        # Initialize file with headers if it doesn't exist
        if not self.ledger_path.exists():
            self._init_ledger()

    def _init_ledger(self) -> None:
        """Create ledger file with headers."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)

    def add_entry(self, data: dict) -> str:
        """
        Append a simplified entry to the ledger.

        Args:
            data: Dict with keys matching headers:
                - date: Transaction date
                - service_name/service: Service name
                - amount: Dollar amount
                - due_date: Due date if applicable
                - category: Category (Expense, Income, etc.)
                - notes: Additional notes
                - source_skill: Which skill generated this entry

        Returns:
            Confirmation message.
        """
        row = [
            data.get("date", datetime.now().strftime("%Y-%m-%d")),
            data.get("service_name", data.get("service", "Unknown")),
            data.get("amount", "0.00"),
            data.get("due_date", ""),
            data.get("category", "Expense"),
            data.get("notes", ""),
            data.get("source_skill", ""),
        ]

        with open(self.ledger_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        return f"Entry added: {row[1]} - ${row[2]}"

    def get_entries(
        self,
        limit: int | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """
        Retrieve entries from the ledger.

        Args:
            limit: Maximum number of entries to return.
            category: Filter by category.

        Returns:
            List of entry dictionaries.
        """
        if not self.ledger_path.exists():
            return []

        entries = []
        with open(self.ledger_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if category and row.get("category") != category:
                    continue
                entries.append(row)
                if limit and len(entries) >= limit:
                    break

        return entries

    def get_total(self, category: str | None = None) -> float:
        """
        Calculate total amount across entries.

        Args:
            category: Optional category filter.

        Returns:
            Total amount.
        """
        entries = self.get_entries(category=category)
        total = 0.0

        for entry in entries:
            amount_str = str(entry.get("amount", "0"))
            amount_str = amount_str.replace("$", "").replace(",", "")
            try:
                total += float(amount_str)
            except ValueError:
                pass

        return total


class SecuritySuite:
    """
    Handles stealth configuration and TOTP generation.

    Provides browser arguments for improved stealth and
    generates OTP codes for 2FA-enabled accounts.
    """

    # Standard stealth arguments for Chromium
    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--hide-scrollbars",
        "--metrics-recording-only",
        "--mute-audio",
        "--no-first-run",
        "--safebrowsing-disable-auto-update",
    ]

    # User agent rotation pool
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.1 Safari/605.1.15",
    ]

    @classmethod
    def get_stealth_args(
        cls,
        window_size: tuple[int, int] = (1920, 1080),
        user_agent: str | None = None,
    ) -> list[str]:
        """
        Return a list of Chrome arguments to improve stealth.

        Args:
            window_size: Browser window dimensions (width, height).
            user_agent: Custom user agent string. If None, uses first default.

        Returns:
            List of Chrome launch arguments.
        """
        args = cls.STEALTH_ARGS.copy()
        args.append(f"--window-size={window_size[0]},{window_size[1]}")

        if user_agent is None:
            user_agent = cls.USER_AGENTS[0]
        args.append(f"--user-agent={user_agent}")

        return args

    @staticmethod
    def generate_otp(secret_key: str | None) -> str:
        """
        Generate a 6-digit TOTP code.

        Args:
            secret_key: Base32-encoded TOTP secret.

        Returns:
            6-digit OTP code or error message.
        """
        if pyotp is None:
            return "Error: pyotp library not installed. Run 'pip install pyotp'"

        if not secret_key:
            return "Error: No secret key provided."

        try:
            # Clean the secret key
            clean_secret = secret_key.replace(" ", "").upper()
            totp = pyotp.TOTP(clean_secret)
            return totp.now()
        except Exception as e:
            return f"Error generating OTP: {e}"

    @staticmethod
    def get_otp_remaining_seconds(secret_key: str | None = None) -> int:
        """
        Get seconds remaining until current OTP expires.

        Args:
            secret_key: Optional secret (not used, standard 30s interval).

        Returns:
            Seconds remaining (0-30).
        """
        if pyotp is None:
            return 0

        import time
        return 30 - (int(time.time()) % 30)
