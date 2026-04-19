import html as html_module
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.constants import ChatAction
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

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

ERROR_MESSAGE = "Произошла ошибка. Попробуйте позже."
API_ERROR = "Сервис временно недоступен. Попробуйте позже."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "• /translate — перевод русский - болгарский\n"
        "• /stress — расстановка ударений\n"
        "• /examples — примеры использования слов\n"
        "• /toggle_stress — вкл/выкл ударения в переводе\n\n"
        "Текущий режим: Перевод"
    )


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "translate")
    await update.message.reply_text("Выбран режим «Перевод»")


async def stress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "stress")
    await update.message.reply_text("Выбран режим «Ударения»")


async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    state.set_user_mode(chat_id, "examples")
    await update.message.reply_text("Выбран режим «Примеры»")


async def toggle_stress_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = str(update.message.from_user.id)
    new_value = state.toggle_stress(chat_id)
    label = "ВКЛ" if new_value else "ВЫКЛ"
    await update.message.reply_text(f"Ударения в переводе: {label}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.message.from_user.id)
    text = update.message.text

    if not text:
        return

    mode = state.get_user_mode(chat_id)

    await update.message.chat.send_action(action=ChatAction.TYPING)

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


async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"DEBUG: Received update: {update.to_dict()}")


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(15)
        .read_timeout(15)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("stress", stress_command))
    app.add_handler(CommandHandler("examples", examples_command))
    app.add_handler(CommandHandler("toggle_stress", toggle_stress_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.ALL, debug_handler))
    app.add_error_handler(error_handler)

    async def set_commands(application):
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Запустить бота"),
                BotCommand("translate", "Перевод русский - болгарский"),
                BotCommand("stress", "Расстановка ударений"),
                BotCommand("examples", "Примеры использования слов"),
                BotCommand("toggle_stress", "Вкл/выкл ударения в переводе"),
            ]
        )

    app.post_init = set_commands

    logger.info("Starting bot in polling mode")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
