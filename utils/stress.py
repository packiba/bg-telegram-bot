"""Bulgarian stress accent placement via rechnik.chitanka.info dictionary parser."""

import asyncio
import functools
import logging
import re
import unicodedata
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BULGARIAN_VOWELS = set("аеиоуъАЕИОУЪ")
BULGARIAN_VOWELS_WITH_YU_YA = set("аеиоуъюяАЕИОУЪЮЯ")
COMBINING_GRAVE = "\u0300"
COMBINING_ACUTE = "\u0301"
COMBINING_RANGE = ("\u0300", "\u036f")

_CHITANKA_BASE = "https://rechnik.chitanka.info"
_SESSION: Optional[aiohttp.ClientSession] = None

_TOKEN_RE = re.compile(r"([\u0400-\u04ff]+(?:['-][\u0400-\u04ff]+)*)", re.UNICODE)
_LANG_MARKER_RE = re.compile(r"\s*LANG:(BG|RU)\s*", re.IGNORECASE)
_SPAN_STRESSED_RE = re.compile(r'id="name-stressed_\d+"[^>]*>([^<]+)</span>')
_CYR_WITH_ACCENT_RE = re.compile(r"[\u0400-\u04ff][\u0400-\u04ff\u0300\u0301]+")
_BASE_FORM_RE = re.compile(
    r"производна\s+форма.*?<a\s+href=\"(/w/[^\"]+)\"",
    re.IGNORECASE | re.DOTALL,
)


def _count_vowels(word: str) -> int:
    stripped = _strip_accents(word)
    return sum(1 for ch in stripped if ch in BULGARIAN_VOWELS_WITH_YU_YA)


def _strip_accents(s: str) -> str:
    result = (
        unicodedata.normalize("NFD", s)
        .replace(COMBINING_GRAVE, "")
        .replace(COMBINING_ACUTE, "")
        .replace("\u0301", "")
    )
    return unicodedata.normalize("NFC", result)


def _vowel_positions(word: str) -> list[int]:
    positions = []
    for i, ch in enumerate(word):
        if _strip_accents(ch) in BULGARIAN_VOWELS_WITH_YU_YA:
            positions.append(i)
    return positions


def _stressed_vowel_index(stressed_word: str) -> int:
    nfd = unicodedata.normalize("NFD", stressed_word)
    nfc = unicodedata.normalize("NFC", stressed_word)
    nfc_idx = 0
    nfd_idx = 0
    nfc_to_nfd = []
    while nfc_idx < len(nfc):
        nfc_to_nfd.append(nfd_idx)
        nfd_idx += 1
        while (
            nfd_idx < len(nfd)
            and COMBINING_RANGE[0] <= nfd[nfd_idx] <= COMBINING_RANGE[1]
        ):
            nfd_idx += 1
        nfc_idx += 1

    vowel_idxs = _vowel_positions(nfc)
    for vi in range(len(vowel_idxs)):
        nfc_pos = vowel_idxs[vi]
        nf_start = nfc_to_nfd[nfc_pos]
        nf_end = nfc_to_nfd[nfc_pos + 1] if nfc_pos + 1 < len(nfc_to_nfd) else len(nfd)
        segment = nfd[nf_start:nf_end]
        if COMBINING_GRAVE in segment or COMBINING_ACUTE in segment:
            return vi
    return -1


def _apply_stress(word: str, vowel_index: int) -> str:
    positions = _vowel_positions(word)
    if vowel_index < 0 or vowel_index >= len(positions):
        return word
    vowel_pos = positions[vowel_index]
    chars = list(word)
    chars.insert(vowel_pos + 1, COMBINING_GRAVE)
    return unicodedata.normalize("NFC", "".join(chars))


def _decode_html_entities(text: str) -> str:
    def _dec_dec(m: re.Match) -> str:
        return chr(int(m.group(1), 10))

    def _dec_hex(m: re.Match) -> str:
        return chr(int(m.group(1), 16))

    text = re.sub(r"&#(\d+);", _dec_dec, text)
    text = re.sub(r"&#x([0-9a-fA-F]+);", _dec_hex, text)
    return text


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession()
    return _SESSION


async def _fetch_chitanka_word(word: str) -> Optional[str]:
    try:
        session = await _get_session()
        url = f"{_CHITANKA_BASE}/w/{word}"
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, timeout=timeout) as resp:
            if resp.status == 200:
                return await resp.text()
            return None
    except Exception as e:
        logger.warning(f"HTTP fetch failed for '{word}': {e}")
        return None


def _extract_stressed_from_html(html: str, plain_word_lower: str) -> Optional[str]:
    html = _decode_html_entities(html)

    m = _SPAN_STRESSED_RE.search(html)
    while m:
        candidate = m.group(1).strip()
        if _strip_accents(candidate).lower() == plain_word_lower:
            return candidate
        m = _SPAN_STRESSED_RE.search(html, m.end())

    html_nfd = unicodedata.normalize("NFD", html)
    freq: dict[str, int] = {}
    for cm in _CYR_WITH_ACCENT_RE.finditer(html_nfd):
        raw = unicodedata.normalize("NFC", cm.group(0))
        plain = _strip_accents(raw).lower()
        if plain == plain_word_lower and raw != plain:
            freq[raw] = freq.get(raw, 0) + 1

    if not freq:
        return None
    return max(freq, key=freq.get)


def _extract_base_form_path(html: str) -> Optional[str]:
    m = _BASE_FORM_RE.search(html)
    return m.group(1) if m else None


# Simple in-memory cache for word stress lookups
_stress_cache: dict[str, str] = {}


async def _lookup_word_stress(word: str) -> str:
    # Check cache first
    if word in _stress_cache:
        logger.debug(f"[Lookup] Cache hit for '{word}'")
        return _stress_cache[word]

    logger.debug(f"[Lookup] Cache miss for '{word}', fetching...")
    stripped = _strip_accents(word)
    if _count_vowels(stripped) <= 1:
        _stress_cache[word] = word
        return word

    clean_lower = stripped.lower()
    clean_word = re.sub(r"[^\u0400-\u04ff]", "", clean_lower)
    if not clean_word:
        _stress_cache[word] = word
        return word

    logger.debug(f"[Lookup] Looking up stress for: '{clean_word}'")

    html = await _fetch_chitanka_word(clean_word)
    if html:
        logger.debug(f"[Lookup] Got HTML for '{clean_word}' ({len(html)} bytes)")
        direct = _extract_stressed_from_html(html, clean_word)
        if direct:
            logger.debug(f"[Lookup] Found direct match: '{direct}'")
            _stress_cache[word] = direct
            return direct
        else:
            logger.debug(f"[Lookup] No direct match found in HTML")
    else:
        logger.debug(f"[Lookup] No HTML received for '{clean_word}'")

    if html:
        base_path = _extract_base_form_path(html)
        if base_path:
            base_word = base_path.replace("/w/", "")
            logger.debug(f"[Lookup] Trying base form: '{base_word}'")
            base_html = await _fetch_chitanka_word(base_word)
            if base_html:
                base_clean = re.sub(r"[^\u0400-\u04ff]", "", base_word.lower())
                stressed_base = _extract_stressed_from_html(base_html, base_clean)
                if stressed_base:
                    logger.debug(f"[Lookup] Found base form stress: '{stressed_base}'")
                    vi = _stressed_vowel_index(stressed_base)
                    if vi >= 0:
                        vowel_idxs = _vowel_positions(clean_word)
                        target_vi = vi if vi < len(vowel_idxs) else len(vowel_idxs) - 1
                        result = _apply_stress(clean_word, target_vi)
                        logger.debug(f"[Lookup] Applied stress to original word: '{result}'")
                        _stress_cache[word] = result
                        return result

    logger.debug(f"[Lookup] Stress lookup failed for '{word}', returning original")
    _stress_cache[word] = word
    return word


async def add_stress_to_text(text: str, force_bulgarian: bool = False) -> str:
    logger.info(f"[Stress] Input text (force_bg={force_bulgarian}): '{text[:100]}...'")

    if not force_bulgarian:
        if not re.search(r"LANG:BG", text, re.IGNORECASE):
            logger.info("[Stress] No LANG:BG marker found, returning original text")
            return text
        text = _LANG_MARKER_RE.sub("", text).strip()
        logger.info(f"[Stress] After removing LANG:BG: '{text[:100]}...'")

    tokens = _TOKEN_RE.split(text)
    logger.info(f"[Stress] Split into {len(tokens)} tokens: {tokens[:10]}")
    processed: list[str] = []
    words_processed = 0

    for i, token in enumerate(tokens):
        logger.debug(f"[Stress] Token {i}: '{token}' (even={i%2==0})")
        if i % 2 == 0:
            processed.append(token)
            continue

        vowel_count = _count_vowels(token)
        logger.debug(f"[Stress] Token '{token}' has {vowel_count} vowels")
        if vowel_count <= 1:
            logger.debug(f"[Stress] Skipping '{token}' (≤1 vowel)")
            processed.append(token)
            continue

        stressed = await _lookup_word_stress(token)
        if stressed and stressed != token:
            words_processed += 1
            is_capital = token[0].isupper() and not token[0].islower()
            if is_capital:
                result = stressed[0].upper() + stressed[1:]
                logger.info(f"[Stress] '{token}' → '{result}' (capitalized)")
                processed.append(result)
            else:
                logger.info(f"[Stress] '{token}' → '{stressed}'")
                processed.append(stressed)
        else:
            logger.debug(f"[Stress] No stress found for '{token}'")
            processed.append(token)

    final_result = "".join(processed)
    logger.info(f"[Stress] Processed {words_processed} words. Result: '{final_result[:100]}...'")
    return final_result
