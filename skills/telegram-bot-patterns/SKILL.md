# Skill: telegram-bot-patterns

## Overview

Use this skill when working with the python-telegram-bot v20+ framework, implementing handlers, inline keyboards, or bot architecture patterns for the Bulgarian-Russian translator bot.

## When to Use

- Modifying `bot.py` or `webhook_app.py`
- Adding new bot handlers or commands
- Implementing inline keyboards or callback queries
- Debugging bot behavior
- Setting up webhook or polling

## Framework: python-telegram-bot v20+

### Key Differences from v13
- All methods are async
- `Updater` removed, use `ApplicationBuilder`
- `context.bot_data` → `context.application.bot_data`
- Handlers use `async def`

### Application Setup

#### Polling Mode
```python
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.run_polling()
```

#### Webhook Mode
```python
app = ApplicationBuilder().token(TOKEN).build()
# Add handlers...
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=WEBHOOK_URL,
    webhook_url=WEBHOOK_URL
)
```

## Handler Patterns

### Command Handler
```python
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Перевод", callback_data="translate"),
        InlineKeyboardButton("Ударения", callback_data="stress"),
        InlineKeyboardButton("Примеры", callback_data="examples")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите режим работы бота:", reply_markup=reply_markup)
```

### Callback Handler
```python
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Remove loading indicator
    
    mode = query.data
    chat_id = query.from_user.id
    
    # Save mode
    await set_user_mode(str(chat_id), mode)
    
    # Confirm
    mode_names = {"translate": "Перевод", "stress": "Ударения", "examples": "Примеры"}
    await query.message.reply_text(f"Режим \"{mode_names[mode]}\" активирован!")
```

### Message Handler
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.from_user.id)
    text = update.message.text
    
    # Show typing
    await update.message.chat.send_action(action="typing")
    
    # Get mode
    mode = await get_user_mode(chat_id)
    
    # Route
    if mode == "translate":
        await handle_translate(chat_id, text, update.message)
    elif mode == "stress":
        await handle_stress(chat_id, text, update.message)
    elif mode == "examples":
        await handle_examples(chat_id, text, update.message)
```

## Inline Keyboard Patterns

### Single Row
```python
keyboard = [[
    InlineKeyboardButton("Button 1", callback_data="action1"),
    InlineKeyboardButton("Button 2", callback_data="action2")
]]
```

### Multiple Rows
```python
keyboard = [
    [InlineKeyboardButton("Row 1", callback_data="r1")],
    [InlineKeyboardButton("Row 2", callback_data="r2")],
    [InlineKeyboardButton("Row 3", callback_data="r3")]
]
```

### Edit Existing Message
```python
await query.edit_message_text("New text", reply_markup=new_keyboard)
```

## Error Handling

### Handler-Level
```python
async def safe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Handler logic
        pass
    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
```

### Application-Level
```python
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

app.add_error_handler(error_handler)
```

## Chat Actions

### Show Typing
```python
await update.message.chat.send_action(action="typing")
# Or for callback queries:
await query.message.chat.send_action(action="typing")
```

### Available Actions
- `ChatAction.TYPING` - Typing indicator
- `ChatAction.UPLOAD_PHOTO` - Uploading photo
- `ChatAction.RECORD_VOICE` - Recording voice

## Message Formatting

### Parse Modes
```python
# HTML
await message.reply_text("<b>Bold</b> <i>Italic</i>", parse_mode="HTML")

# Markdown
await message.reply_text("*Bold* _Italic_", parse_mode="Markdown")
```

### HTML Tags Supported
- `<b>bold</b>`
- `<i>italic</i>`
- `<u>underline</u>`
- `<s>strikethrough</s>`
- `<a href="url">link</a>`
- `<code>code</code>`
- `<pre>preformatted</pre>`

## Webhook Setup

### Set Webhook
```python
import requests

def set_webhook(bot_token: str, webhook_url: str):
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/setWebhook",
        data={"url": webhook_url}
    )
    return response.json()
```

### Delete Webhook
```python
def delete_webhook(bot_token: str):
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    )
    return response.json()
```

### Get Webhook Info
```python
def get_webhook_info(bot_token: str):
    response = requests.get(
        f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    )
    return response.json()
```

## Best Practices

### Do
- Use `await query.answer()` for all callbacks
- Show typing action for long operations
- Use `filters.TEXT` to only handle text messages
- Store chat_id as string (can be negative for groups)
- Use `ApplicationBuilder` for configuration
- Handle errors gracefully

### Don't
- Block the handler thread (use async I/O)
- Send multiple messages without delay
- Ignore callback queries (causes loading indicator)
- Store sensitive data in bot_data
- Use synchronous HTTP in handlers
- Hardcode bot token

## Testing

### Manual Testing
```python
# Test bot initialization
from bot import main
import asyncio

# Mock update for testing
class MockUpdate:
    def __init__(self, text):
        self.message = MockMessage(text)

class MockMessage:
    def __init__(self, text):
        self.text = text
        self.from_user = MockUser(123)
        self.chat = MockChat()

class MockUser:
    def __init__(self, id):
        self.id = id

class MockChat:
    async def send_action(self, action):
        pass
```

### Logging
```python
import logging

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
```

## Reference

- python-telegram-bot docs: https://docs.python-telegram-bot.org
- Telegram Bot API: https://core.telegram.org/bots/api
- v20 migration guide: https://docs.python-telegram-bot.org/en/stable/migration.html
