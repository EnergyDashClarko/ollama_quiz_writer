#!/usr/bin/env python3
"""
Discord Quiz Bot - Main Entry Point

This script runs the Discord quiz bot. Configure your bot token in config.json
or set the DISCORD_BOT_TOKEN environment variable.

Usage:
    python main.py

Configuration:
    1. Copy config.json and set your Discord bot token
    2. Or set DISCORD_BOT_TOKEN environment variable
    3. Customize quiz settings in config.json as needed

Environment Variables:
    DISCORD_BOT_TOKEN: Your Discord bot token (overrides config.json)
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def load_config():
    """Load configuration from config.json file."""
    config_path = Path("config.json")
    
    if not config_path.exists():
        print("❌ Error: config.json not found!")
        print("Please copy config.json and configure your Discord bot token.")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in config.json: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        sys.exit(1)

def get_bot_token(config):
    """Get bot token from environment variable or config file."""
    # Environment variable takes precedence
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        return token
    
    # Fall back to config file
    token = config.get('bot', {}).get('token')
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Discord bot token not configured!")
        print("Either:")
        print("  1. Set DISCORD_BOT_TOKEN environment variable")
        print("  2. Update the 'token' field in config.json")
        sys.exit(1)
    
    return token

def setup_logging_from_config(config):
    """Set up logging based on configuration."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    log_directory = Path(log_config.get('log_directory', './logs/'))
    
    # Create logs directory
    log_directory.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_directory / "bot.log", encoding='utf-8')
        ]
    )

async def run_bot_with_config():
    """Run the bot with configuration."""
    # Load configuration
    config = load_config()
    
    # Set up logging
    setup_logging_from_config(config)
    
    # Get bot token
    token = get_bot_token(config)
    
    # Import and run bot
    from src.bot import run_bot
    await run_bot(token, config)

if __name__ == "__main__":
    try:
        print("🤖 Starting Discord Quiz Bot...")
        asyncio.run(run_bot_with_config())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        sys.exit(1)