# Skill: openrouter-integration

## Overview

Use this skill when working with the OpenRouter API integration for the Bulgarian-Russian translator bot. Covers API configuration, retry logic, system prompts, and error handling.

## When to Use

- Modifying `utils/openrouter.py`
- Changing LLM model or system prompts
- Debugging API errors
- Adding new API-based features
- Optimizing API usage

## API Configuration

### Endpoint
```
POST https://openrouter.ai/api/v1/chat/completions
```

### Headers
```
Authorization: Bearer {OPENROUTER_API_KEY}
Content-Type: application/json
```

### Request Body
```json
{
  "model": "google/gemini-3-flash-preview",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.5
}
```

### Response
```json
{
  "choices": [
    {
      "message": {
        "content": "translated text\nLANG:BG"
      }
    }
  ]
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | Required. API key from openrouter.ai |
| `OPENROUTER_MODEL` | `google/gemini-3-flash-preview` | Model identifier |

## System Prompts

### Translation Prompt
```
Ты — эксперт-лингвист и носитель русского и болгарского языков. Твоя задача — выполнять двусторонний перевод (Русский ↔ Болгарский) на уровне живой разговорной речи.

1. Автоопределение: Если ввод на русском — переведи на болгарский. Если ввод на болгарском — переведи на русский.

2. Качество перевода: Избегай дословных калек и буквализма. Используй естественные для носителей устойчивые выражения, идиомы и фразеологизмы. Перевод должен звучать так, будто его написал местный житель.

3. Контекст и эмоции: Полностью сохраняй эмоциональный окрас и стиль оригинала. Если фраза двусмысленна, выбирай наиболее часто используемый разговорный вариант.

4. Язык вывода: ВАЖНО — если переводишь на болгарский, добавь в конце ответа на новой строке маркер: LANG:BG. Если переводишь на русский — маркер: LANG:RU.

5. Формат ответа: Присылай ТОЛЬКО текст перевода и маркер языка. Строго запрещено добавлять кавычки, пояснения (типа «Перевод:»), комментарии или варианты. Только чистый результат и маркер.
```
**Temperature:** 0.5

### Examples Prompt
```
Действуй как носитель болгарского языка. Дай 3 коротких, реалистичных примера использования слова/фразы. Используй живой разговорный язык, сленг или типичные бытовые ситуации (без цензуры здравого смысла и излишней вежливости). Примеры должны отражать, как люди реально общаются на улице или в кругу друзей. Каждый пример на новой строке, пронумерован. Только болгарский текст, без лишних пояснений.
```
**Temperature:** 0.6

## Retry Logic

### Exponential Backoff
```
Attempt 0: immediate
Attempt 1: wait 1 second
Attempt 2: wait 2 seconds
Attempt 3: wait 4 seconds → final failure
```

### Implementation
```python
async def _make_request(messages, temperature):
    max_retries = 3
    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait_time = 2 ** (attempt - 1)  # 1, 2, 4
            await asyncio.sleep(wait_time)
        
        try:
            # Make request
            return response
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            continue
    
    return error_message
```

### Error Messages
On final failure: `"Сервис временно недоступен. Попробуйте позже."`

## Session Management

### Module-Level Session
```python
_session: aiohttp.ClientSession | None = None

async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=15)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session

async def _close_session():
    global _session
    if _session and not _session.closed:
        await _session.close()
```

### Timeout Configuration
```python
aiohttp.ClientTimeout(
    total=15,      # Total request timeout
    connect=5,     # Connection timeout
    sock_read=10   # Socket read timeout
)
```

## Public API

### translate_text(text: str) -> str
```python
async def translate_text(text: str) -> str:
    """
    Translate text between Russian and Bulgarian.
    
    Args:
        text: Input text (Russian or Bulgarian)
    
    Returns:
        Translated text with LANG:BG or LANG:RU marker
    """
```

### get_examples(text: str) -> str
```python
async def get_examples(text: str) -> str:
    """
    Generate 3 conversational examples for a Bulgarian word/phrase.
    
    Args:
        text: Bulgarian word or phrase
    
    Returns:
        Numbered list of examples
    """
```

## Error Handling

### Missing API Key
```python
if not os.getenv("OPENROUTER_API_KEY"):
    logger.error("OPENROUTER_API_KEY not set")
    return "Сервис временно недоступен. Попробуйте позже."
```

### HTTP Errors
- 401: Invalid API key → log error, return error message
- 429: Rate limited → respect `Retry-After` header, then retry
- 500: Server error → retry with backoff
- 503: Service unavailable → retry with backoff

### Response Validation
```python
def _extract_response(data: dict) -> str | None:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        logger.error(f"Unexpected response format: {data}")
        return None
```

## Available Models

### Recommended
- `google/gemini-3-flash-preview` - Fast, good quality, free tier available

### Alternatives
- Check https://openrouter.ai/models for full list
- Filter by "Free" tier for zero-cost operation
- Test model changes with sample translations

## Cost Management

### Free Tier
- Some models have free quotas
- Monitor usage at https://openrouter.ai/activity

### Rate Limits
- Default: varies by model
- Check response headers for limits
- Implement client-side rate limiting if needed

### Optimization
- Cache translations for common phrases (future)
- Use flash models for cost efficiency
- Batch requests when possible (future)

## Testing

### Manual Test
```bash
# Test translation
python -c "
import asyncio
from utils.openrouter import translate_text
print(asyncio.run(translate_text('Привет, как дела?')))
"

# Test examples
python -c "
import asyncio
from utils.openrouter import get_examples
print(asyncio.run(get_examples('здрасти')))
"
```

### API Key Validation
```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemini-3-flash-preview",
    "messages": [{"role": "user", "content": "Say hello"}]
  }'
```

## Troubleshooting

### Common Issues

**Empty response:**
- Check API key is valid
- Verify model name is correct
- Check OpenRouter account status

**Timeout errors:**
- Increase timeout in ClientTimeout
- Check network connectivity
- Try alternative model

**Rate limiting:**
- Implement client-side rate limiting
- Add longer delays between retries
- Consider upgrading API tier

**Unexpected response format:**
- Log full response for debugging
- Check OpenRouter API changelog
- Update response parsing if needed

## Reference

- OpenRouter API: https://openrouter.ai/docs
- Models: https://openrouter.ai/models
- Pricing: https://openrouter.ai/pricing
