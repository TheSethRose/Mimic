"""
Custom/domain-specific tools for the skills player.

These tools are specific to certain use cases (e.g., banking, finance)
and can be optionally loaded. Keep the core tools.py clean and generic.
"""

import csv
import os
from pathlib import Path
from typing import TYPE_CHECKING

from .automation_suite import FileOrganizer, Ledger, SecuritySuite

if TYPE_CHECKING:
    from browser_use import ActionResult, Tools


def register_finance_tools(tools: "Tools") -> None:
    """
    Register finance/banking-related tools.

    Args:
        tools: Tools instance to register actions on.
    """
    from browser_use import ActionResult

    @tools.action(
        description="""Summarize transaction data from a CSV file. Use after
        downloading bank transaction CSVs to analyze financial data. Calculates
        total transactions, debits, credits, net change, and current balance."""
    )
    def summarize_transactions(
        file_path: str,
        account_name: str = "Unknown Account",
    ) -> ActionResult:
        """
        Parse and summarize a bank transaction CSV file.

        Args:
            file_path: Path to the CSV file to analyze.
            account_name: Name of the account for the summary header.

        Returns:
            ActionResult with transaction summary or error.
        """
        path = Path(file_path)
        if not path.exists():
            return ActionResult(
                error=f"File not found: {file_path}",
                include_in_memory=True
            )

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError as e:
            return ActionResult(
                error=f"Could not read file: {e}",
                include_in_memory=True
            )

        lines = content.strip().split('\n')
        if not lines:
            return ActionResult(
                error="CSV file is empty",
                include_in_memory=True
            )

        reader = csv.DictReader(lines)
        rows = list(reader)

        if not rows:
            return ActionResult(
                extracted_content=f"Account: {account_name}\nNo transactions.",
                include_in_memory=True
            )

        total_debits = 0.0
        total_credits = 0.0
        dates: list[str] = []
        current_balance: float | None = None

        # Column name variants for different banks
        date_columns = [
            'Transaction Date', 'Date', 'Trans Date', 'Posted Date'
        ]
        balance_columns = [
            'Balance', 'Running Balance', 'Available Balance'
        ]
        amount_columns = ['Amount', 'Transaction Amount', 'Amt']
        debit_columns = ['Debit', 'Withdrawal', 'Withdrawals', 'Money Out']
        credit_columns = ['Credit', 'Deposit', 'Deposits', 'Money In']

        for row in rows:
            # Extract date
            for key in date_columns:
                if key in row and row[key]:
                    date_val = row[key].strip().replace('"', '')
                    dates.append(date_val)
                    break

            # Extract balance (only first row needed)
            if current_balance is None:
                for key in balance_columns:
                    if key in row and row[key]:
                        try:
                            bal = row[key].strip()
                            bal = bal.replace('"', '').replace('$', '')
                            bal = bal.replace(',', '')
                            current_balance = float(bal)
                            break
                        except ValueError:
                            pass

            # Extract amount from combined column
            for key in amount_columns:
                if key in row and row[key]:
                    amount_str = row[key].strip().replace('"', '')
                    credits, debits = _parse_amount(amount_str)
                    total_credits += credits
                    total_debits += debits
                    break

            # Check separate debit/credit columns
            for key in debit_columns:
                if key in row and row[key]:
                    try:
                        val = row[key].strip()
                        val = val.replace('"', '').replace('$', '')
                        val = val.replace(',', '').replace('-', '')
                        if val:
                            total_debits += float(val)
                    except ValueError:
                        pass

            for key in credit_columns:
                if key in row and row[key]:
                    try:
                        val = row[key].strip()
                        val = val.replace('"', '').replace('$', '')
                        val = val.replace(',', '').replace('+', '')
                        if val:
                            total_credits += float(val)
                    except ValueError:
                        pass

        # Build summary
        net_change = total_credits - total_debits
        if len(dates) >= 2:
            date_range = f"{dates[-1]} to {dates[0]}"
        elif dates:
            date_range = dates[0]
        else:
            date_range = "Unknown"

        if current_balance is not None:
            balance_str = f"${current_balance:,.2f}"
        else:
            balance_str = "Unknown"

        summary = f"""
📊 Account Summary: {account_name}
{'=' * 50}
📅 Date Range: {date_range}
📝 Total Transactions: {len(rows)}
💵 Current Balance: {balance_str}

💰 Financial Summary:
   Credits (Money In):  ${total_credits:,.2f}
   Debits (Money Out):  ${total_debits:,.2f}
   ─────────────────────────────
   Net Change:          ${net_change:+,.2f}
"""
        print(summary)

        return ActionResult(
            extracted_content=summary,
            include_in_memory=True
        )

    # Initialize shared instances for file organization and ledger
    _organizer = FileOrganizer()
    _ledger = Ledger()

    @tools.action(
        description="""Organize a downloaded file (PDF, statement, etc.) into a
        structured folder hierarchy. Automatically categorizes by service type
        (Utilities, Financial, Retail, Healthcare) and renames using pattern:
        YYYY-MM-DD_ServiceName_$Amount.ext"""
    )
    def organize_file(
        source_path: str,
        service_name: str,
        amount: str = "0.00",
        date: str = "",
        category: str = "",
    ) -> ActionResult:
        """
        Organize and rename a downloaded file.

        Args:
            source_path: Path to the downloaded file.
            service_name: Name of the service/vendor.
            amount: Dollar amount (optional).
            date: Date string YYYY-MM-DD (optional, defaults to today).
            category: Override auto-detection (optional).

        Returns:
            ActionResult with new file path or error.
        """
        metadata = {
            "service_name": service_name,
            "amount": amount,
        }
        if date:
            metadata["date"] = date
        if category:
            metadata["category"] = category

        result = _organizer.organize(source_path, metadata)

        if result.startswith("Error"):
            return ActionResult(error=result, include_in_memory=True)

        return ActionResult(
            extracted_content=result,
            include_in_memory=True
        )

    @tools.action(
        description="""Log a financial entry to the ledger for tracking.
        Use after extracting bill amounts, transaction data, or payment info.
        Creates a running record in CSV format for analysis."""
    )
    def log_to_ledger(
        service_name: str,
        amount: str,
        date: str = "",
        due_date: str = "",
        category: str = "Expense",
        notes: str = "",
    ) -> ActionResult:
        """
        Add an entry to the financial ledger.

        Args:
            service_name: Name of the service/vendor.
            amount: Dollar amount.
            date: Transaction date (defaults to today).
            due_date: Payment due date (optional).
            category: Expense, Income, Bill, Retail, etc.
            notes: Additional notes.

        Returns:
            ActionResult confirming entry was logged.
        """
        entry = {
            "service_name": service_name,
            "amount": amount,
            "category": category,
            "notes": notes,
        }
        if date:
            entry["date"] = date
        if due_date:
            entry["due_date"] = due_date

        result = _ledger.add_entry(entry)

        return ActionResult(
            extracted_content=result,
            include_in_memory=True
        )

    @tools.action(
        description="""Generate a TOTP (Time-based One-Time Password) code for
        2FA authentication. Requires the TOTP secret key (base32 encoded) which
        is typically provided during initial 2FA setup."""
    )
    def generate_otp(
        secret_env_var: str,
    ) -> ActionResult:
        """
        Generate a 6-digit OTP code from a TOTP secret.

        Args:
            secret_env_var: Name of environment variable containing the
                           TOTP secret (e.g., "AMAZON_OTP_SECRET").

        Returns:
            ActionResult with 6-digit OTP code or error.
        """
        secret = os.getenv(secret_env_var)

        if not secret:
            return ActionResult(
                error=f"Environment variable {secret_env_var} not set",
                include_in_memory=True
            )

        code = SecuritySuite.generate_otp(secret)

        if code.startswith("Error"):
            return ActionResult(error=code, include_in_memory=True)

        remaining = SecuritySuite.get_otp_remaining_seconds()

        return ActionResult(
            extracted_content=f"OTP Code: {code} (expires in {remaining}s)",
            include_in_memory=True
        )


def _parse_amount(amount_str: str) -> tuple[float, float]:
    """
    Parse an amount string and return (credits, debits).

    Handles formats like "+ $123.45", "- $123.45", or plain numbers.

    Args:
        amount_str: The amount string to parse.

    Returns:
        Tuple of (credit_amount, debit_amount).
    """
    clean_val = amount_str.replace('$', '').replace(',', '').strip()
    credits = 0.0
    debits = 0.0

    try:
        if clean_val.startswith('+'):
            credits = float(clean_val[1:].strip())
        elif clean_val.startswith('-'):
            debits = float(clean_val[1:].strip())
        else:
            amount = float(clean_val)
            if amount >= 0:
                credits = amount
            else:
                debits = abs(amount)
    except ValueError:
        pass

    return credits, debits
