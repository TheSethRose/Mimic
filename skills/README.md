# Browser Automation Skills

This directory contains browser automation skills created from Chrome DevTools Recorder exports.

## Structure

Skills are organized by category in subdirectories:

- `bills/` - Bill payment and financial account skills
- `shopping/` - E-commerce and shopping skills (future)
- `forms/` - Form filling and submission skills (future)
- `data/` - Data extraction and reporting skills (future)

## Usage

### List available skills
```bash
python agents/chrome_recorder.py list
```

### Play a skill
```bash
python agents/chrome_recorder.py play skills/bills/pnc-transactions.json
```

### Play with data extraction
```bash
python agents/chrome_recorder.py play skills/bills/pnc-transactions.json --extract
```

### Custom extraction
```bash
python agents/chrome_recorder.py play skills/bills/kia-finance.json \
  --extract-prompt "Get the monthly payment and due date"
```

### Run headless (no UI)
```bash
python agents/chrome_recorder.py play skills/bills/grayson-bill.json --headless
```

## Creating New Skills

> **Note**: I would highly recommend using Claude Opus or Google Gemini 3 to refine
> the skill JSON after exporting from Chrome Recorder.

1. Open Chrome DevTools (F12)
2. Go to the **Recorder** tab (⋮ → More tools → Recorder)
3. Click "Create a new recording"
4. Perform the automation steps in the browser
5. Click "End recording"
6. Export as JSON (dropdown next to the replay button)
7. Save to this directory under an appropriate category folder
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
    "EMAIL": "Service login email",
    "PASSWORD": "Service login password"
  },
  "extract_prompt": "Extract and summarize account balance and due date",
  "steps": [
    // ... Chrome Recorder steps
  ]
}
```

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
PNC_USER_ID=username
PNC_PASSWORD=password
KIA_USERNAME=username
KIA_PASSWORD=password
```

Then in skill JSON:
```json
{
  "value": "{{PNC_USER_ID}}"
}
```
