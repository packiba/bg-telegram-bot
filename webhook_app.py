import html as html_module
import logging
import os

from aiohttp import web
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
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

telegram_app = None


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/translate — перевод русский - болгарский\n"
        "/stress — расстановка ударений\n"
        "/examples — примеры использования слов"
    )


async def handle_translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "translate")
    await update.message.reply_text("Выбран режим «Перевод»")


async def handle_stress_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "stress")
    await update.message.reply_text("Выбран режим «Ударения»")


async def handle_examples_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "examples")
    await update.message.reply_text("Выбран режим «Примеры»")


async def handle_toggle_stress_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    new_value = state.toggle_stress(chat_id)
    label = "ВКЛ" if new_value else "ВЫКЛ"
    await update.message.reply_text(f"Ударения в переводе: {label}")


async def handle_examples_style_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    new_style = state.cycle_examples_style(chat_id)
    label = state.STYLE_LABELS.get(new_style, new_style)
    await update.message.reply_text(f"Стиль примеров: {label}")


async def handle_creativity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    new_temp = state.cycle_temperature(chat_id)
    label = state.TEMPERATURE_LABELS.get(new_temp, new_temp)
    await update.message.reply_text(f"Креативность: {label}")


async def handle_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    settings = state.get_all_settings(chat_id)

    mode_labels = {
        "translate": "Перевод",
        "stress": "Ударения",
        "examples": "Примеры"
    }
    mode_label = mode_labels.get(settings["mode"], settings["mode"])
    stress_label = "ВКЛ" if settings["stress_enabled"] else "ВЫКЛ"

    message = (
        "Настройки бота\n\n"
        f"Режим работы: {mode_label}\n"
        f"Ударения в переводе: {stress_label}\n\n"
        f"Стиль примеров: {settings['examples_style_label']}\n"
        f"Креативность: {settings['temperature_label']}\n\n"
        "Команды:\n"
        "/examples_style — изменить стиль примеров\n"
        "/creativity — изменить креативность"
    )

    await update.message.reply_text(message)


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
    logger.info(f"[Translate] User {chat_id} requested translation: '{text[:50]}...'")
    result = await openrouter.translate_text(text, chat_id)

    if result == API_ERROR:
        await message.reply_text(result)
        return

    logger.info(f"[Translate] Translation result: '{result[:100]}...'")

    is_bulgarian = "LANG:BG" in result.upper()
    stress_enabled = state.get_stress_enabled(chat_id)
    logger.info(f"[Translate] is_bulgarian={is_bulgarian}, stress_enabled={stress_enabled}")

    if is_bulgarian and stress_enabled:
        logger.info(f"[Translate] Applying stress to: '{result[:100]}...'")
        stressed = await stress.add_stress_to_text(result)
        logger.info(f"[Translate] After stress: '{stressed[:100]}...'")
        result = stressed
    else:
        logger.info(f"[Translate] Skipping stress (bg={is_bulgarian}, enabled={stress_enabled})")

    result = result.replace("LANG:BG", "").replace("LANG:RU", "").strip()
    logger.info(f"[Translate] Final result: '{result[:100]}...'")

    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def handle_stress(chat_id: str, text: str, message) -> None:
    result = await stress.add_stress_to_text(text, force_bulgarian=True)
    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def handle_examples(chat_id: str, text: str, message) -> None:
    result = await openrouter.get_examples(text, chat_id)
    escaped = html_module.escape(result)
    await message.reply_text(escaped, parse_mode="HTML")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)


async def post_shutdown(app) -> None:
    logger.info("Shutting down...")
    await openrouter._close_session()
    if stress._SESSION and not stress._SESSION.closed:
        await stress._SESSION.close()


async def init_telegram_app():
    global telegram_app
    telegram_app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(15)
        .read_timeout(15)
        .post_shutdown(post_shutdown)
        .build()
    )

    telegram_app.add_handler(CommandHandler("start", handle_start))
    telegram_app.add_handler(CommandHandler("translate", handle_translate_cmd))
    telegram_app.add_handler(CommandHandler("stress", handle_stress_cmd))
    telegram_app.add_handler(CommandHandler("examples", handle_examples_cmd))
    telegram_app.add_handler(CommandHandler("toggle_stress", handle_toggle_stress_cmd))
    telegram_app.add_handler(CommandHandler("examples_style", handle_examples_style_cmd))
    telegram_app.add_handler(CommandHandler("creativity", handle_creativity_cmd))
    telegram_app.add_handler(CommandHandler("settings", handle_settings_cmd))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    telegram_app.add_error_handler(error_handler)

    # Initialize the application
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram app initialized and started")

    # Register bot commands in menu
    await telegram_app.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("translate", "Перевод русский - болгарский"),
        BotCommand("stress", "Расстановка ударений"),
        BotCommand("examples", "Примеры использования слов"),
        BotCommand("toggle_stress", "Вкл/выкл ударения в переводе"),
        BotCommand("examples_style", "Стиль примеров (вежливый/разговорный/грубый)"),
        BotCommand("creativity", "Креативность (низкая/средняя/высокая)"),
        BotCommand("settings", "Показать текущие настройки"),
    ])
    logger.info("Bot commands registered in menu")

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")

    return telegram_app


async def webhook(request):
    try:
        if not telegram_app:
            logger.warning("Telegram app not initialized yet")
            return web.Response(status=503, text="Not ready")

        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)

        if update:
            await telegram_app.process_update(update)
        return web.Response()
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return web.Response(status=500)


async def health(request):
    return web.Response(text="OK")


async def on_startup(app):
    await init_telegram_app()


async def on_shutdown(app):
    logger.info("Shutting down application...")

    # Close HTTP sessions first
    logger.info("Closing aiohttp sessions...")
    await openrouter._close_session()
    if stress._SESSION and not stress._SESSION.closed:
        await stress._SESSION.close()

    # Then stop telegram app
    if telegram_app:
        logger.info("Stopping telegram app...")
        await telegram_app.stop()
        await telegram_app.shutdown()

    logger.info("Shutdown complete")


def get_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/webhook", webhook)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    app = get_app()
    port = int(os.getenv("PORT", 5000))
    web.run_app(app, host="0.0.0.0", port=port)