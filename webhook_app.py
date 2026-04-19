import asyncio
import html as html_module
import logging
import os

from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from utils import openrouter, state, stress

load_dotenv()

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set")
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

ERROR_MESSAGE = "Произошла ошибка. Попробуйте позже."
API_ERROR = "Сервис временно недоступен. Попробуйте позже."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    text = update.message.text

    if not text:
        return

    mode = state.get_user_mode(chat_id)

    try:
        if mode == "translate":
            await handle_translate(chat_id, text, update.message)
        elif mode == "stress":
            await handle_stress(chat_id, text, update.message)
        elif mode == "examples":
            await handle_examples(chat_id, text, update.message)
    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        await update.message.reply_text(ERROR_MESSAGE)


async def handle_translate(chat_id: str, text: str, message) -> None:
    result = await openrouter.translate_text(text)

    if result == API_ERROR:
        await message.reply_text(result)
        return

    if "LANG:BG" in result.upper() and state.get_stress_enabled(chat_id):
        stressed = await stress.add_stress_to_text(result)
        result = stressed

    result = result.replace("LANG:BG", "").replace("LANG:RU", "").strip()

    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def handle_stress(chat_id: str, text: str, message) -> None:
    result = await stress.add_stress_to_text(text, force_bulgarian=True)
    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def handle_examples(chat_id: str, text: str, message) -> None:
    result = await openrouter.get_examples(text)
    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)


async def post_shutdown(app) -> None:
    logger.info("Shutting down...")
    await openrouter._close_session()
    if stress._SESSION and not stress._SESSION.closed:
        await stress._SESSION.close()


async def webhook(request):
    try:
        app = request.app
        update = Update.parse_obj(request.data)
        if update:
            await app.process_update(update)
        return web.Response()
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(status=500)


async def health(request):
    return web.Response(text="OK")


async def start_webhook_app():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(15)
        .read_timeout(15)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")

    runner = web.AppRunner(app.Application)
    await runner.setup()

    port = int(os.getenv("PORT", 5000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    webhook_app = web.Application()
    webhook_app.app = app.Application
    webhook_app.router.add_post("/webhook", webhook)
    webhook_app.router.add_get("/health", health)

    return webhook_app


def main():
    import signal

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = loop.run_until_complete(start_webhook_app())

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))


if __name__ == "__main__":
    main()