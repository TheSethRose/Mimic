#!/usr/bin/env python3
"""
Mimic - Browser Automation with Muscle Memory.

Turn Chrome Recordings into Unbreakable AI Agents.

Usage:
    python main.py list
    python main.py play skills/bills/example.json
    python main.py play skills/login.json --loose
    python main.py play skills/scrape.json --extract
"""

from skills_player.cli import main

if __name__ == "__main__":
    main()
