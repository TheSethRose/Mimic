# Browser Automation Skills

This directory contains browser automation skills created from Chrome DevTools Recorder exports.

## Structure

```
skills/
├── public/                              # Shared example skills
│   ├── amazon-alexa-shopping-list.json  # Get Alexa shopping list
│   ├── amazon-orders.json               # Get Amazon order history
│   ├── walmart-shopping-list-to-cart.json  # Search & add to Walmart cart
│   ├── walmart-purchase-history.json    # Get Walmart orders
│   ├── sams-club-shopping-list-to-cart.json  # Search & add to Sam's cart
│   └── sams-club-order-history.json     # Get Sam's Club orders
├── private/                             # Personal skills (gitignored)
│   ├── anna-water-bill.json
│   ├── grayson-bill.json
│   ├── kia-finance.json
│   └── pnc-transactions.json
├── .preferences.json                    # MFA preferences (auto-generated)
└── README.md
```

## Quick Start - Natural Language

Use `mimic.py` for natural language automation - the AI figures out which skills to run:

```bash
# Interactive mode
python mimic.py

# Use natural language - AI decides what to run
python mimic.py "Get my Alexa shopping list"
python mimic.py "Get my Alexa shopping list and add items to Walmart cart"
python mimic.py "Check all my bills and bank balance"

# Preview mode (see what would run)
python mimic.py --dry-run "Check all my bills"

# List available skills
python mimic.py skills
```

## Running Individual Skills

### List available skills
```bash
python mimic.py skills
```

### Play a skill
```bash
python mimic.py play skills/private/my-skill.json
```

### Play with data extraction
```bash
python mimic.py play skills/private/bank-login.json --extract
```

### Loose mode (adaptive)
```bash
python mimic.py play skills/private/dashboard.json --loose
```

### Custom extraction prompt
```bash
python mimic.py play skills/private/account.json \
  --extract-prompt "Get the monthly payment and due date"
```

### Run headless (no UI)
```bash
python mimic.py play skills/private/check-balance.json --headless
```

## Available Tools

Skills have access to these agent tools during execution:

### Interactive Tools
- `ask_user_for_input` - Prompt for MFA codes, choices
- `notify_and_wait` - Notify user and wait for acknowledgment

### Finance Tools
- `summarize_transactions` - Parse and summarize bank CSV exports
- `organize_file` - Auto-file downloaded documents
- `log_to_ledger` - Add entries to financial ledger
- `generate_otp` - Generate TOTP codes for 2FA

## Creating New Skills

1. Open Chrome DevTools (`F12`)
2. Go to the **Recorder** tab (`⋮` → More tools → Recorder)
3. Click "Create a new recording"
4. Perform the automation steps in the browser
5. Click "End recording"
6. Export as JSON
7. Save to `skills/private/` (or `skills/public/` if sharing)
8. Edit the JSON to:
   - Replace hardcoded credentials with `{{ENV_VAR}}` placeholders
   - Add a `"title"` and `"description"`
   - Add `"env_vars"` with descriptions
   - Optionally add `"extract_prompt"` for data extraction

### Skill File Structure

```json
{
  "title": "Service Name - Description",
  "description": "What this skill does",
  "may_require_mfa": true,
  "env_vars": {
    "SERVICE_EMAIL": "Service login email",
    "SERVICE_PASSWORD": "Service login password",
    "SERVICE_OTP_SECRET": "Optional: TOTP secret for 2FA"
  },
  "extract_prompt": "Extract and summarize account balance and due date",
  "steps": [
    // ... Chrome Recorder steps
  ]
}
```

### Semantic Selectors

For resilient skills that survive website changes, use multiple selector strategies:

```json
{
  "type": "click",
  "selectors": [
    ["#email"],
    ["name/email"],
    ["aria/Email Address"],
    ["text/Email"]
  ]
}
```

Priority order:
1. ID selectors (`#id`)
2. Name attributes (`name/field`)
3. ARIA labels (`aria/Label`)
4. Text content (`text/Button Text`)

## MFA Preferences

The system saves your MFA preferences (delivery method, trust device, terms acceptance) to `.preferences.json`. These are auto-applied when available, but you'll always be asked for actual verification codes.

To reset preferences:
```bash
rm skills/.preferences.json
```

## Environment Variables

All credentials should be stored in `.env` and referenced as placeholders in skills:

```env
# Example .env

# Amazon
AMAZON_EMAIL=your_email
AMAZON_PASSWORD=your_password
AMAZON_OTP_SECRET=JBSWY3DPEHPK3PXP

# Walmart
WALMART_EMAIL=your_email
WALMART_PASSWORD=your_password

# Sam's Club
SAMS_EMAIL=your_email
SAMS_PASSWORD=your_password

# Bank
PNC_USERNAME=your_username
PNC_PASSWORD=your_password

# Utilities
ANNA_EMAIL=your_email
ANNA_PASSWORD=your_password
```

Then in skill JSON:
```json
{
  "value": "{{BANK_USERNAME}}"
}
```

## Public Skills

### Amazon Skills

#### `amazon-alexa-shopping-list.json`
Extracts items from your Alexa Shopping List.

**Required:** `AMAZON_EMAIL`, `AMAZON_PASSWORD`
**Optional:** `AMAZON_OTP_SECRET` for auto-2FA

**Returns:**
```json
{"shopping_list": [{"item_name": "Milk", "quantity": 1}]}
```

#### `amazon-orders.json`
Extracts recent Amazon order history.

**Required:** `AMAZON_EMAIL`, `AMAZON_PASSWORD`

**Returns:**
```json
{"orders": [{"order_date": "...", "order_number": "...", "total": "$X.XX", "items": [...]}]}
```

### Walmart Skills

#### `walmart-shopping-list-to-cart.json`
Searches Walmart for items and adds previously-purchased, in-stock items to cart.

**Required:** `WALMART_EMAIL`, `WALMART_PASSWORD`
**Input:** Shopping list array
**Behavior:** Adds to cart, does NOT checkout

#### `walmart-purchase-history.json`
Extracts Walmart order history.

**Required:** `WALMART_EMAIL`, `WALMART_PASSWORD`

### Sam's Club Skills

#### `sams-club-shopping-list-to-cart.json`
Searches Sam's Club for items and adds previously-purchased, in-stock items to cart.

**Required:** `SAMS_EMAIL`, `SAMS_PASSWORD`
**Input:** Shopping list array
**Behavior:** Adds to cart, does NOT checkout

#### `sams-club-order-history.json`
Extracts Sam's Club order history.

**Required:** `SAMS_EMAIL`, `SAMS_PASSWORD`
