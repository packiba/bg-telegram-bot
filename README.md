# Русско-болгарский переводчик с ударениями

Telegram-бот для двустороннего перевода между русским и болгарским языками с автоматической расстановкой ударений и генерацией разговорных примеров.

## Возможности

- **Перевод** — двусторонний перевод русский ↔ болгарский с живым разговорным стилем (OpenRouter API, Google Gemini)
- **Ударения** — автоматическая расстановка ударений в болгарском тексте (словарь rechnik.chitanka.info)
- **Примеры** — генерация 3 реалистичных разговорных примеров для болгарских слов

## Быстрый старт

### Требования

- Python 3.10+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenRouter API Key (бесплатная регистрация на [openrouter.ai](https://openrouter.ai))

### Установка

1. Клонировать репозиторий:
   ```bash
   git clone <repo-url>
   cd bg-telegram-bot
   ```

2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Создать файл `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Заполнить `.env`:
   - `TELEGRAM_BOT_TOKEN` — токен от @BotFather
   - `OPENROUTER_API_KEY` — ключ от OpenRouter

5. Запустить:
   ```bash
   python bot.py
   ```

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Да | — | Токен бота от @BotFather |
| `OPENROUTER_API_KEY` | Да | — | API-ключ OpenRouter |
| `OPENROUTER_MODEL` | Нет | `google/gemini-3-flash-preview` | Модель для перевода |
| `DATABASE_PATH` | Нет | `data/bot.db` | Путь к SQLite базе |

## Развёртывание на JustRunMy.App

[JustRunMy.App](https://justrunmy.app) — контейнерный хостинг с автоматическим HTTPS, логами и 24/7 uptime. Бесплатный тариф: 0.15 vCPU, 0.25 GB RAM, 0.3 GB диск.

### Шаг 1: Подготовка ZIP-архива

Скачайте проект как ZIP или создайте архив:

```bash
# Исключая ненужные файлы
zip -r bot.zip bot.py utils/ requirements.txt .env.example Dockerfile .dockerignore LICENSE README.md
```

Или просто скачайте репозиторий как ZIP через GitHub.

### Шаг 2: Регистрация

1. Зарегистрируйтесь на [justrunmy.app](https://justrunmy.app/id/Account/Register)
2. Войдите в [панель управления](https://justrunmy.app/panel)

### Шаг 3: Создание приложения

1. Нажмите **"Create Application"**
2. Выберите **"Upload ZIP"**
3. Загрузите ZIP-архив проекта
4. Выберите образ: **Python 3.11**

### Шаг 4: Настройка переменных окружения

В панели приложения добавьте переменные:

| Переменная | Значение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Ваш токен от @BotFather |
| `OPENROUTER_API_KEY` | Ваш ключ от OpenRouter |
| `OPENROUTER_MODEL` | `google/gemini-3-flash-preview` (опционально) |
| `DATABASE_PATH` | `/app/data/bot.db` |

### Шаг 5: Запуск

1. Нажмите **"Start"**
2. Бот запустится в режиме polling
3. Проверьте логи — должно быть `"Starting bot in polling mode"`
4. Откройте бота в Telegram и отправьте `/start`

### Обновление бота

1. Внесите изменения в код
2. Создайте новый ZIP
3. В панели приложения нажмите **"Redeploy"** и загрузите новый архив

### Логи и мониторинг

- **Logs** — вкладка "Logs" в панели, фильтрация по ключевым словам
- **Web Shell** — вкладка "Shell" для доступа к контейнеру
- **Auto-restart** — бот автоматически перезапускается при сбое

### Persistent disk

Для сохранения базы данных между перезапусками:

1. В панели приложения перейдите в **"Disks"**
2. Создайте диск (минимум 0.3 GB)
3. Смонтируйте в `/app/data`
4. Перезапустите приложение

Без persistent disk база `data/bot.db` будет сброшена при каждом редиплое.

## Локальная разработка

```bash
pip install -r requirements.txt
# Создать .env с TELEGRAM_BOT_TOKEN и OPENROUTER_API_KEY
python bot.py
```

Бот запустится в режиме long polling.

## Docker (локально)

```bash
docker build -t bg-telegram-bot .
docker run -d \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e OPENROUTER_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  --name bg-bot \
  bg-telegram-bot
```

## API и источники

- **OpenRouter API** — [openrouter.ai](https://openrouter.ai)
- **Словарь ударений** — [rechnik.chitanka.info](https://rechnik.chitanka.info)
- **Telegram Bot API** — [core.telegram.org/bots/api](https://core.telegram.org/bots/api)

## Архитектура

```
bg-telegram-bot/
├── bot.py                  # Точка входа (polling mode)
├── utils/
│   ├── __init__.py
│   ├── openrouter.py       # Перевод и примеры (OpenRouter API)
│   ├── stress.py           # Расстановка ударений (chitanka.info)
│   └── state.py            # Хранение режимов (SQLite + lru_cache)
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

## Устранение неполадок

### Бот не отвечает

1. Проверьте логи в панели JustRunMy.App
2. Убедитесь что `TELEGRAM_BOT_TOKEN` правильный
3. Проверьте что бот запущен (статус "Running")

### Ошибки API-ключа

```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemini-3-flash-preview","messages":[{"role":"user","content":"test"}]}'
```

### База данных не сохраняется

Убедитесь что persistent disk смонтирован в `/app/data`. Без него данные теряются при редиплое.

## Roadmap

- [ ] Кэширование ударений через Redis (Upstash)
- [ ] Поддержка дополнительных языков
- [ ] Логирование ошибок в Telegram-канал администратора
- [ ] Rate limiting для защиты API
- [ ] Команда /help с справкой по режимам
- [ ] Кнопка «Отмена» для сброса режима

## Лицензия

MIT License — см. [LICENSE](LICENSE)

## Контакты

Открыт для контрибьюторов и предложений. Создавайте Issues и Pull Requests.
