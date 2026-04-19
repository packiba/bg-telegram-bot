import aiohttp
import asyncio
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not OPENROUTER_API_KEY:
    logger.error("OPENROUTER_API_KEY not set")

TRANSLATION_SYSTEM_PROMPT = (
    "Ты — эксперт-лингвист и носитель русского и болгарского языков. "
    "Твоя задача — выполнять двусторонний перевод (Русский ↔ Болгарский) "
    "на уровне живой разговорной речи.\n\n"
    "1. Автоопределение: Если ввод на русском — переведи на болгарский. "
    "Если ввод на болгарском — переведи на русский.\n\n"
    "2. Качество перевода: Избегай дословных калек и буквализма. "
    "Используй естественные для носителей устойчивые выражения, идиомы и "
    "фразеологизмы. Перевод должен звучать так, будто его написал местный житель.\n\n"
    "3. Контекст и эмоции: Полностью сохраняй эмоциональный окрас и стиль "
    "оригинала. Если фраза двусмысленна, выбирай наиболее часто используемый "
    "разговорный вариант.\n\n"
    "4. Язык вывода: ВАЖНО — если переводишь на болгарский, добавь в конце "
    "ответа на новой строке маркер: LANG:BG. Если переводишь на русский — "
    "маркер: LANG:RU.\n\n"
    "5. Формат ответа: Присылай ТОЛЬКО текст перевода и маркер языка. "
    "Строго запрещено добавлять кавычки, пояснения (типа «Перевод:»), "
    "комментарии или варианты. Только чистый результат и маркер."
)

EXAMPLES_SYSTEM_PROMPT = (
    "Действуй как носитель болгарского языка. Дай 3 коротких, реалистичных "
    "примера использования слова/фразы. Используй живой разговорный язык, "
    "сленг или типичные бытовые ситуации (без цензуры здравого смысла и "
    "излишней вежливости). Примеры должны отражать, как люди реально общаются "
    "на улице или в кругу друзей. Каждый пример на новой строке, пронумерован. "
    "Только болгарский текст, без лишних пояснений."
)

ERROR_MESSAGE = "Сервис временно недоступен. Попробуйте позже."

_session: Optional[aiohttp.ClientSession] = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session


async def _close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


def _extract_response(data: dict) -> Optional[str]:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        logger.error(f"Unexpected response format: {data}")
        return None


async def _make_request(messages: list[dict], temperature: float) -> Optional[str]:
    max_retries = 3
    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait_time = 2 ** (attempt - 1)
            logger.warning(f"Attempt {attempt} failed, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)

        try:
            session = await _get_session()
            async with session.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                },
            ) as response:
                if response.status == 401:
                    logger.error("Invalid API key")
                    return ERROR_MESSAGE

                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", wait_time))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if response.status >= 500:
                    logger.warning(f"Server error {response.status}")
                    continue

                response.raise_for_status()
                data = await response.json()
                result = _extract_response(data)
                if result:
                    logger.debug(f"Request successful")
                    return result
                continue

        except asyncio.TimeoutError as e:
            logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
            continue
        except aiohttp.ClientError as e:
            logger.warning(f"Client error on attempt {attempt + 1}: {e}")
            continue

    logger.error("All retry attempts failed")
    return ERROR_MESSAGE


async def translate_text(text: str) -> str:
    if not OPENROUTER_API_KEY:
        return ERROR_MESSAGE

    messages = [
        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    result = await _make_request(messages, temperature=0.5)
    return result or ERROR_MESSAGE


async def get_examples(text: str) -> str:
    if not OPENROUTER_API_KEY:
        return ERROR_MESSAGE

    messages = [
        {"role": "system", "content": EXAMPLES_SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    result = await _make_request(messages, temperature=0.6)
    if result and result != ERROR_MESSAGE:
        return f"Примеры:\n\n{result}"
    return result or ERROR_MESSAGE
