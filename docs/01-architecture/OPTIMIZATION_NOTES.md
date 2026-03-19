# OneBox Integrations Hub — Optimization Notes

> Деталізація рекомендацій з [../../ARCHITECTURE_OPTIMIZATION.md](../../ARCHITECTURE_OPTIMIZATION.md)
> Дата: 2026-03-19

---

## Поточні проблеми (специфічні для цього проекту)

### 1. Секрети у workspace (КРИТИЧНО)

`.env` файл у workspace містить реальні credentials:
- `ONEBOX_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `BAF_PASSWORD`
- `DATABASE_URL` з паролем

**Виправити негайно:**
```bash
# 1. Додати до .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore

# 2. Переконатись що .env не в git history
# (якщо є git repo)
git rm --cached .env 2>/dev/null || true

# 3. Залишити тільки .env.example з placeholder values
```

```bash
# .env.example — тільки структура, без реальних значень
ONEBOX_DOMAIN=your-domain.1b.app
ONEBOX_LOGIN=380XXXXXXXXX
ONEBOX_API_KEY=your-api-key-here
ONEBOX_WEBHOOK_SECRET=your-webhook-secret
TELEGRAM_BOT_TOKEN=your-bot-token
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://user:password@db:5432/hub_db
BAF_URL=http://your-baf-host/path
BAF_USER=your-user
BAF_PASSWORD=your-password
```

---

### 2. CORS — занадто широкий

```python
# src/main.py — ЗАРАЗ (небезпечно)
allow_origins=["*"]

# ТРЕБА — конкретні домени
allow_origins=[
    "http://152.53.117.253:5173",   # dev
    "https://your-domain.com",       # production
]
```

---

### 3. Webhook endpoint — HMAC validation

Webhook validation реалізований тільки для OneBox. Для `1c` source — немає перевірки підпису.

```python
# src/api/routes/webhook.py — перевірити
# Якщо BAF/1C не підтримує HMAC, мінімально:
# - IP whitelist для 1C джерел
# - або secret token в query param/header
```

---

### 4. Scheduler — немає retry логіки для помилок

RQ підтримує retry, але потрібно явно налаштувати:

```python
# Рекомендація для кожного scheduler job:
from rq import Retry

queue.enqueue(
    sync_job,
    retry=Retry(max=3, interval=[10, 30, 60])  # 3 спроби з backoff
)
```

---

### 5. Structured logging — додати request ID

Structlog вже є в проекті — варто додати кореляцію запитів:

```python
# src/main.py — middleware
import uuid
import structlog

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

## Що спроектовано добре — не чіпати

### YAML routing rules
```yaml
# config/routing_rules.yaml
```
Чудове рішення — бізнес-логіку маршрутизації подій можна змінювати без деплою коду. Зберігати і розширювати.

### Adapter pattern
`src/adapters/base.py` + окремі адаптери для кожного сервісу — правильна архітектура для інтеграційного хаба. Легко додати новий адаптер.

### Docker Compose структура
4 сервіси (hub, worker, db, redis) з healthcheck — добре. Можна лише додати:

```yaml
# docker-compose.yml — додати restart policy
services:
  hub:
    restart: unless-stopped
  worker:
    restart: unless-stopped
```

### RQ + Redis для async jobs
Правильний вибір для webhook processing (відповідь 200 одразу, обробка асинхронно).

---

## Моніторинг (відсутній — додати)

Мінімальний набір:

```python
# src/api/routes/health.py — розширити
@router.get("/health")
async def health():
    return {
        "status": "ok",
        "redis": await check_redis(),
        "db": await check_db(),
        "queue_size": get_queue_length(),
        "last_sync": get_last_sync_timestamp(),
    }
```

Зовнішній uptime monitor (UptimeRobot, betteruptime) — пінгувати `/health` кожні 5 хв.
