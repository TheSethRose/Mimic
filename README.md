# Mimic

**Browser Automation with Muscle Memory.**

Turn Chrome Recordings into Unbreakable AI Agents.

---

Standard automation breaks the moment a website changes. Mimic uses your Chrome DevTools recordings as a flexible guide, not a rigid script. It combines the speed of recording with the intelligence of an AI agent—adapting to layout shifts, healing broken selectors, and handling MFA challenges in real-time.

**Record once. Run forever.**

## Features

- 🎬 **Chrome Recorder Integration** — Export recordings from Chrome DevTools, run them with AI
- 🧠 **Self-Healing Selectors** — Adapts when elements move or IDs change
- 🔐 **MFA & CAPTCHA Handling** — Interactive prompts for verification challenges
- 🔓 **Loose Mode** — Let the agent reason freely instead of following steps rigidly
- 💾 **Preference Memory** — Remembers your MFA choices (SMS vs Email)
- 📊 **Data Extraction** — Extract structured data after navigation
- 🔒 **Secure Credentials** — Environment variable substitution for sensitive data

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required: Choose one LLM provider
OPENROUTER_API_KEY=your_key_here

# Optional: Configure provider/model
LLM_PROVIDER=openrouter          # openrouter, openai, anthropic
LLM_MODEL=google/gemini-2.5-flash

# Your skill credentials (example)
BANK_USERNAME=your_username
BANK_PASSWORD=your_password
```

### 3. Create a Skill

1. Open Chrome DevTools (`F12`)
2. Click `⋮` → **More tools** → **Recorder**
3. Click **Create a new recording**
4. Perform your actions in the browser
5. Click **End recording**
6. Export as **JSON**
7. Save to `skills/` folder

### 4. Run It

```bash
# List available skills
python main.py list

# Play a skill
python main.py play skills/login.json

# Play with loose mode (adaptive)
python main.py play skills/login.json --loose

# Extract data after navigation
python main.py play skills/dashboard.json --extract
```

## Usage

```
python main.py <command> [options]

Commands:
  list                     List all available skills
  play <skill>             Play a skill file

Options for 'play':
  --extract, -x            Use the skill's built-in extraction prompt
  --extract-prompt, -p     Custom extraction prompt
  --headless               Run browser without UI
  --no-interactive         Disable MFA/user input prompts
  --loose, -l              Adaptive mode: agent reasons freely
```

## Skill Format

Skills are Chrome DevTools Recorder JSON exports with optional extensions:

```json
{
  "title": "Login to Dashboard",
  "description": "Authenticates and navigates to main dashboard",
  "steps": [...],
  
  "env_vars": {
    "SITE_USERNAME": "Your login email",
    "SITE_PASSWORD": "Your login password"
  },
  "extract_prompt": "Get the account balance and last login date",
  "may_require_mfa": true
}
```

### Credential Substitution

Replace sensitive values with `{{ENV_VAR}}` placeholders:

```json
{
  "type": "change",
  "value": "{{SITE_USERNAME}}",
  "selectors": [["#email"]]
}
```

Then add to your `.env`:

```env
SITE_USERNAME=user@example.com
```

## Execution Modes

### Strict Mode (Default)

Follows the recorded steps precisely. Best for stable workflows.

```bash
python main.py play skills/checkout.json
```

### Loose Mode

Provides the goal and hints to the agent, letting it adapt to page changes. Best for sites that update frequently.

```bash
python main.py play skills/checkout.json --loose
```

## MFA Handling

When Mimic encounters verification pages, it will prompt you interactively:

```
============================================================
🔐 USER INPUT REQUIRED
============================================================

📄 What I see on the page:
   A verification code input field. Text says "Enter the 6-digit code sent to your phone"

❓ Please provide the verification code

👤 Your response: _
```

Mimic remembers your preferences (like choosing SMS over Email) for future runs.

## Project Structure

```
mimic/
├── main.py                 # CLI entry point
├── skills_player/          # Core package
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration & constants
│   ├── player.py           # Main orchestration
│   ├── skills.py           # Skill loading & conversion
│   ├── tools.py            # Interactive agent tools
│   ├── custom_tools.py     # Domain-specific tools
│   └── preferences.py      # User preference storage
└── skills/                 # Your skill recordings
    ├── README.md
    └── bills/
        └── example.json
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider: `openrouter`, `openai`, `anthropic` | `openrouter` |
| `LLM_MODEL` | Model name | `google/gemini-2.5-flash` |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `OPENAI_API_KEY` | OpenAI API key (if using openai provider) | — |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using anthropic provider) | — |

## How It Works

1. **Record** — Chrome DevTools Recorder captures your browser actions as JSON
2. **Translate** — Mimic converts rigid selectors into natural language instructions
3. **Execute** — An AI agent interprets the instructions, adapting to the live page
4. **Heal** — When elements change, the agent finds them by context, not just selectors
5. **Interact** — MFA challenges trigger interactive prompts; preferences are saved

## Examples

### Bank Statement Download

```bash
# Record logging into your bank and navigating to statements
# Save as skills/bank-statements.json
# Add credentials to .env

python main.py play skills/bank-statements.json \
  --extract-prompt "Download the most recent statement PDF"
```

### Price Monitoring

```bash
python main.py play skills/check-price.json \
  --loose \
  --extract-prompt "What is the current price?"
```

### Form Automation

```bash
python main.py play skills/submit-form.json --headless
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `uv run ruff check --fix && uv run ruff format`
5. Submit a pull request

## License

MIT

---

**Mimic** — Record once. Run forever.
