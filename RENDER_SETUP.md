# Инструкция по развёртыванию на Render

## Шаг 1: Подготовка проекта

Убедитесь, что в вашем репозитории есть:
- `Dockerfile`
- `requirements.txt`
- `wsgi.py`
- `webhook_app.py`

## Шаг 2: Создание Web Service на Render

1. Зайдите на [https://dashboard.render.com](https://dashboard.render.com)
2. Нажмите **New +** → **Web Service**
3. Подключите ваш GitHub/GitLab репозиторий
4. Настройте параметры:
   - **Name**: `bg-telegram-bot` (или любое имя)
   - **Region**: выберите ближайший регион
   - **Branch**: `master` (или ваша основная ветка)
   - **Runtime**: Docker
   - **Instance Type**: Free

## Шаг 3: Настройка переменных окружения

В разделе **Environment Variables** добавьте:

1. `TELEGRAM_BOT_TOKEN` = `ваш_токен_от_BotFather`
2. `OPENROUTER_API_KEY` = `ваш_ключ_OpenRouter`
3. `WEBHOOK_URL` = `https://ваш-сервис.onrender.com` (заполните после создания)
4. `PORT` = `10000` (или оставьте пустым - Render установит автоматически)
5. `OPENROUTER_MODEL` = `google/gemini-3-flash-preview` (опционально)

**ВАЖНО**: После создания сервиса Render даст вам URL вида:
```
https://bg-telegram-bot-xxxx.onrender.com
```

Вернитесь в настройки → Environment Variables и установите `WEBHOOK_URL` равным этому URL (без `/webhook` на конце).

## Шаг 4: Развёртывание

1. Нажмите **Create Web Service**
2. Дождитесь завершения сборки (может занять 5-10 минут)
3. Проверьте логи - должно появиться сообщение:
   ```
   Webhook set to https://ваш-сервис.onrender.com/webhook
   ```

## Шаг 5: Проверка работы

### Проверка health endpoint:
```bash
curl https://ваш-сервис.onrender.com/health
```
Должно вернуть: `OK`

### Проверка вебхука через Telegram:
1. Отправьте `/start` вашему боту
2. Бот должен ответить меню с режимами

### Проверка логов:
В интерфейсе Render → **Logs** вы увидите:
- Запуск gunicorn
- Инициализацию Telegram приложения
- Установку вебхука
- Входящие запросы от Telegram

## Возможные проблемы

### Бот не отвечает
1. Проверьте логи на Render
2. Убедитесь, что `WEBHOOK_URL` установлен правильно (без слэша на конце)
3. Проверьте, что вебхук установлен:
   ```bash
   python set_webhook.py
   ```

### Ошибка "Telegram app not initialized yet"
Подождите 1-2 минуты - приложение инициализируется асинхронно.

### Сервис засыпает (Free tier)
На бесплатном тарифе Render:
- Сервис засыпает после 15 минут неактивности
- Первый запрос после сна может занять 30+ секунд
- **Решение**: перейдите на платный план ($7/месяц) или используйте ping-сервис

### Переустановка вебхука вручную
```bash
# Локально
export TELEGRAM_BOT_TOKEN="ваш_токен"
export WEBHOOK_URL="https://ваш-сервис.onrender.com"
python set_webhook.py
```

## Мониторинг

Проверить статус вебхука:
```bash
curl "https://api.telegram.org/bot<ваш_токен>/getWebhookInfo"
```

## Отладка

Для более подробного логирования можно добавить переменную окружения:
```
LOG_LEVEL=DEBUG
```

И обновить код webhook_app.py:
```python
level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, level))
```
