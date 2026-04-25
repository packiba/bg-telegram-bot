# Настройка Cloudflare Worker для обхода IP-блокировки

## Зачем это нужно?

Словари Wiktionary и Chitanka блокируют запросы с IP-адресов Render (403 Forbidden).  
**Cloudflare Workers** работает как прокси с другого IP-адреса, обходя блокировку.

- ✅ **100,000 запросов/день бесплатно**
- ✅ Очень быстро (edge CDN)
- ⏱️ **5-10 минут на настройку**

---

## Шаг 1: Регистрация на Cloudflare

1. Перейдите на https://dash.cloudflare.com/sign-up
2. Зарегистрируйтесь (email + пароль)
3. ✅ **Бесплатный план** достаточен!

---

## Шаг 2: Создание Worker

1. В Cloudflare Dashboard перейдите: **Workers & Pages**
2. Нажмите **Create application**
3. Выберите **Create Worker**
4. Дайте имя (например, `bg-dict-proxy`)
5. Нажмите **Deploy**

---

## Шаг 3: Добавление кода

1. После создания нажмите **Edit code**
2. **Удалите** весь существующий код
3. **Скопируйте** содержимое файла `cloudflare-worker.js` из этого репозитория
4. **Вставьте** в редактор
5. Нажмите **Save and Deploy**

---

## Шаг 4: Получение URL

После развёртывания вы увидите URL вида:
```
https://bg-dict-proxy.your-username.workers.dev
```

**Скопируйте этот URL!** Он понадобится на следующем шаге.

---

## Шаг 5: Настройка бота

### Локально (.env файл):

Добавьте в файл `.env`:
```env
CLOUDFLARE_WORKER_URL=https://bg-dict-proxy.your-username.workers.dev
```

### На Render:

1. Откройте ваш сервис на https://dashboard.render.com
2. Перейдите в **Environment**
3. Нажмите **Add Environment Variable**
4. Добавьте:
   - Key: `CLOUDFLARE_WORKER_URL`
   - Value: `https://bg-dict-proxy.your-username.workers.dev`
5. Нажмите **Save Changes**
6. Render автоматически задеплоит заново

---

## Шаг 6: Проверка

### Тест Worker напрямую:

Откройте в браузере:
```
https://bg-dict-proxy.your-username.workers.dev?word=куче&source=wiktionary
```

Должен вернуться JSON с данными из Wiktionary (не 403!).

### Тест бота:

1. Напишите боту: `/toggle_stress` → "ВКЛ"
2. Отправьте: `собака`
3. Должно вернуться: `кучѐ` (с ударением!)

### Проверка логов на Render:

```
[Fetch] Requesting via Cloudflare Worker: ...
[Fetch] Wiktionary response status: 200 ✅
[Lookup] Found in Wiktionary: 'ку̀че' ✅
```

Если видите эти строки - **всё работает!** 🎉

---

## Troubleshooting

### Worker возвращает 403

- Проверьте, что код Worker скопирован полностью
- Убедитесь, что Worker задеплоен (Save and Deploy)

### Бот не использует Worker

- Проверьте переменную `CLOUDFLARE_WORKER_URL` на Render
- Убедитесь, что URL **без слеша** на конце
- Проверьте логи - должно быть "Requesting via Cloudflare Worker"

### Worker не отвечает

- Проверьте лимиты на https://dash.cloudflare.com/
- Free план: 100,000 запросов/день (достаточно для бота)

---

## Лимиты Free плана

- **100,000 запросов/день**
- **10ms CPU time на запрос**
- Этого **более чем достаточно** для Telegram бота

Если вдруг превысите (маловероятно для личного бота):
- Worker будет возвращать ошибку
- Бот вернётся к прямым запросам (которые могут блокироваться)
- Лимит обновляется каждый день

---

## Мониторинг

Статистика Worker:  
https://dash.cloudflare.com/ → Workers & Pages → ваш worker → **Analytics**

Можно видеть:
- Количество запросов
- Ошибки
- Latency

---

## Безопасность

Worker доступен публично (любой может отправить запрос). Это нормально, потому что:
- Нет секретов в Worker
- Cloudflare автоматически защищает от DDoS
- Free план имеет лимит 100k запросов/день

Если хотите ограничить доступ, можно добавить проверку API ключа в Worker код.
