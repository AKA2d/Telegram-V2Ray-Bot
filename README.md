# Telegram V2Ray Bot

A Python-based Telegram bot for selling V2Ray subscriptions through a PasarGuard-compatible panel.

## Overview

This repository contains a Telegram bot built with `aiogram`, using PostgreSQL as the database backend. The bot is configured by environment variables loaded from `telegram-bot/bot/.env`.

## Requirements

- Python 3.11+
- PostgreSQL database
- `pip` package manager
- `docker` is optional but not required for local development

## Setup

### 1. Create and activate the virtual environment

```powershell
cd C:\Users\Ali\Documents\Telegram-V2Ray-Bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure PostgreSQL

The bot expects a PostgreSQL database connection string in `telegram-bot/bot/.env`.

Example:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/botdb
```

If you do not have the database created yet, create it manually or with your own tooling.

### 4. Configure environment variables

Edit `telegram-bot/bot/.env` and provide the required values:

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_TELEGRAM_ID`
- `PANEL_BASE_URL`
- `PANEL_USERNAME`
- `PANEL_PASSWORD`
- `DATABASE_URL`
- `REQUIRED_CHANNEL_ID` (optional)
- `DIRECT_NODE_TAGS` (optional)
- `SESSION_SECRET` (optional)

## Running the bot

From the repository root:

```powershell
cd C:\Users\Ali\Documents\Telegram-V2Ray-Bot\telegram-bot
..\ .venv\Scripts\python.exe main.py
```

or if the virtual environment is already active:

```powershell
cd telegram-bot
python main.py
```

## Notes

- The bot uses `python-dotenv` to load `telegram-bot/bot/.env`.
- The local database is created and migrated automatically by the bot when it starts, using SQLAlchemy metadata.
- If Telegram responds with token validation or API errors, verify the `TELEGRAM_BOT_TOKEN` value and ensure the token is active.

## Project structure

- `telegram-bot/main.py` — bot entrypoint
- `telegram-bot/bot/config.py` — environment and configuration loading
- `telegram-bot/bot/db.py` — async SQLAlchemy engine and initialization
- `telegram-bot/bot/handlers/` — bot command and message handlers
- `requirements.txt` — pinned Python dependencies

## License

MIT
