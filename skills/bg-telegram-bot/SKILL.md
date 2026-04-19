# Skill: bg-telegram-bot

## Overview

This skill provides domain-specific knowledge for developing and maintaining the Bulgarian-Russian Translator Telegram bot. Use it when working on any aspect of this project.

## Project Context

**Purpose:** Telegram bot with three modes:
1. **Translation** (RU ↔ BG) - Auto-detects language, uses OpenRouter API
2. **Stress** (Ударения) - Adds stress marks to Bulgarian text via rechnik.chitanka.info
3. **Examples** (Примеры) - Generates 3 conversational examples for Bulgarian words

**Tech Stack:**
- Python 3.10+
- python-telegram-bot v20+ (async)
- Flask (webhook mode)
- aiohttp (HTTP client)
- BeautifulSoup4 (HTML parsing)
- SQLite (user state persistence)
- python-dotenv (env var management)

**Architecture:**
```
bulgarian_bot/
├── bot.py                  # Main entry point (polling or webhook auto-detect)
├── webhook_app.py          # Flask app for webhook deployment
├── utils/
│   ├── __init__.py
│   ├── openrouter.py       # translate_text(), get_examples() + retry
│   ├── stress.py           # add_stress_to_text() + chitanka parser
│   └── state.py            # SQLite CRUD + lru_cache for user modes
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

## Core Workflows

### User Mode Selection
1. `/start` → InlineKeyboard: [Перевод | Ударения | Примеры]
2. User clicks → `state.set_user_mode(chat_id, mode)` → Confirmation message
3. Mode persists in SQLite across restarts
4. Default mode: `translate`

### Translation Flow
1. User sends text → `state.get_user_mode(chat_id)` → Route to handler
2. `translate` → `openrouter.translate_text(text)` → Returns text with `LANG:BG` or `LANG:RU` marker
3. If `LANG:BG` → `stress.add_stress_to_text(translated_text)` → Adds stress marks
4. Strip markers → Send to user

### Stress Flow
1. User sends Bulgarian text → `stress.add_stress_to_text(text, force_bulgarian=True)`
2. Tokenize → Lookup each word in rechnik.chitanka.info
3. Apply stress marks → Return with accents

### Examples Flow
1. User sends Bulgarian word/phrase → `openrouter.get_examples(text)`
2. Format with "Примеры:\n\n" header → Send to user

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | From @BotFather |
| `OPENROUTER_API_KEY` | Yes | - | From openrouter.ai |
| `OPENROUTER_MODEL` | No | `google/gemini-3-flash-preview` | LLM model |
| `WEBHOOK_URL` | No | - | If set, enables webhook mode |
| `DATABASE_PATH` | No | `data/bot.db` | SQLite file path |
| `HOST` | No | `0.0.0.0` | Flask bind address |
| `PORT` | No | `5000` | Flask port |

## Key Implementation Details

### State Management (utils/state.py)
- SQLite table: `user_modes(chat_id TEXT PRIMARY KEY, mode TEXT, updated_at TIMESTAMP)`
- `lru_cache(maxsize=1024)` on reads
- Cache invalidation on writes
- Thread-safe via `check_same_thread=False`

### Stress Dictionary Parser (utils/stress.py)
- Primary: Parse `span[id^="name-stressed_"]`
- Fallback: Find Cyrillic tokens with `\u0300`/`\u0301`
- Lemmatization: Follow "производна форма" links
- `lru_cache(maxsize=5000)` at word level
- 10s timeout on HTTP requests

### OpenRouter Client (utils/openrouter.py)
- Retry: 3 attempts with exponential backoff (1s → 2s → 4s)
- Timeout: 15s per request
- Translation temperature: 0.5
- Examples temperature: 0.6
- Error fallback: "Сервис временно недоступен. Попробуйте позже."

## Development Guidelines

### Code Style
- Type hints on all functions
- f-strings over .format()
- pathlib.Path over os.path
- Async/await for all I/O
- Logging over print()

### Error Handling
- Never crash on external service failure
- Log at appropriate levels (DEBUG for success, WARNING for retries, ERROR for failures)
- Return graceful fallbacks to users
- No stack traces in user messages

### Testing
- Test with real Bulgarian text including edge cases
- Verify stress marks render correctly in Telegram
- Test mode switching and persistence
- Test webhook vs polling modes

## Common Tasks

### Adding a New Mode
1. Add mode constant to `utils/state.py` validation
2. Create handler in `bot.py`
3. Add button to inline keyboard
4. Update this skill documentation

### Updating Stress Parser
1. Test against rechnik.chitanka.info structure changes
2. Update fallback parsing logic
3. Verify cache invalidation if needed

### Changing LLM Model
1. Update `OPENROUTER_MODEL` env var
2. Adjust system prompts if needed
3. Test translation quality

## External APIs

### OpenRouter
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Auth: `Authorization: Bearer {key}`
- Docs: https://openrouter.ai/docs

### rechnik.chitanka.info
- Format: `https://rechnik.chitanka.info/w/{word}`
- No auth required
- Rate limit: be respectful, cache aggressively

### Telegram Bot API
- Via python-telegram-bot library
- Webhook requires HTTPS
- Long polling works everywhere

## Deployment Targets

1. **Local** - `python bot.py` (polling)
2. **PythonAnywhere** - Flask webhook, renew every 3 months
3. **Oracle Cloud Free Tier** - VM with systemd service
4. **Koyeb/Render** - Auto-deploy from Git, webhook mode

## Reference Files

- `ref/Переводчик РУ-БГ с режимами.json` - Working n8n workflow (source of truth for behavior)
- `CLAUDE.md` - Full project specification
- `agents/` - Agent definitions for autonomous work
