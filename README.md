# StackView

Backend и лендинг формы обратной связи для страницы разработчика.

Реализована валидация, rate limit, AI-обогащение, email, сохранение в PostgreSQL, метрики и OpenAPI.

## Демо

| Способ | Что проверить | Почта                                                                                                                                                                                                                     |
|--------|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **[https://stackview-api.onrender.com](https://stackview-api.onrender.com)** | Лендинг, API, AI, БД, метрики, Swagger | На **Render Free** исходящие SMTP-порты `25` / `465` / `587` **заблокированы** платформой — письма через Yandex с деплоя могут не уходить (`email_send_failed` / timeout). Это ограничение хостинга, не логики приложения. |
| **Локальный запуск** (инструкция ниже) | Полный сценарий end-to-end | SMTP (Yandex и др.) работает с вашей машины — удобно проверить оба письма.                                                                                                                                             |

Полезные URL на Render:

- Сайт: https://stackview-api.onrender.com/
- Health: https://stackview-api.onrender.com/api/health
- OpenAPI UI: https://stackview-api.onrender.com/api/docs
- Metrics: https://stackview-api.onrender.com/api/metrics

Free-инстанс Render после простоя "засыпает", первый запрос может занять 30–60 секунд.

---

## 1. Как запустить проект

### Требования

- Python 3.12–3.14
- Poetry
- PostgreSQL
- (опционально) SMTP
- (опционально) ключ OpenAI-compatible API (Groq / OpenAI)

### Установка

```bash
git clone https://github.com/simbarilion/StackView.git
cd StackView
poetry install
cp .env.example .env
```

Отредактируйте `.env` (см. таблицу ниже).

### Миграции и seed

```bash
poetry run alembic upgrade head
poetry run seed
```

`seed` добавляет демо-обращения, если таблица пуста; при уже существующих записях пропускается.

### Запуск API + лендинга

```bash
make run
# или:
poetry run uvicorn app.main:app --reload
```

Откройте http://127.0.0.1:8000/ и http://127.0.0.1:8000/api/docs.

### Полезные команды

```bash
make test      # pytest
make lint      # ruff
make format    # ruff format + fix
```

### Переменные окружения

Скопируйте из `.env.example`. Основные имена:

| Группа | Переменные |
|--------|------------|
| Приложение | `APP_NAME`, `APP_ENV` (`development` / `production`), `APP_DEBUG`, `APP_HOST`, `APP_PORT`, `CORS_ORIGINS` |
| Логи | `LOG_LEVEL`, `LOG_DIR`, `LOG_FILE`, `REQUEST_LOG_FILE` |
| Файловые данные | `DATA_DIR` (rate limit JSON) |
| БД локально | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| БД на Render | `DATABASE_URL` (подставляется Render; локально не обязателен) |
| Rate limit | `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` |
| SMTP | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `MAIL_FROM`, `MAIL_TO_OWNER` |
| AI | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `AI_TIMEOUT_SECONDS`, `AI_ENABLED` |

**Пример SMTP (Yandex, порт 465):**

```env
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_TLS=false
SMTP_USE_SSL=true
SMTP_USERNAME=...
SMTP_PASSWORD=...
MAIL_FROM=...
MAIL_TO_OWNER=...
```

**Пример AI (Groq, OpenAI-compatible SDK):**

```env
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
AI_ENABLED=true
```

Поведение почты:

- `APP_ENV=development` и SMTP не задан → обращение принимается, `email_sent=false`
- `APP_ENV=production` и SMTP не задан → **502** `email_not_configured`

---

## 2. Стек технологий

### Backend

| Слой | Технологии |
|------|------------|
| Язык | Python 3.12+ |
| API | FastAPI, Uvicorn |
| Конфиг | pydantic-settings |
| БД | PostgreSQL, SQLAlchemy 2 (async + asyncpg), Alembic, psycopg2 (миграции) |
| Почта | aiosmtplib, Jinja2 (шаблоны писем) |
| HTTP-клиент | httpx (через OpenAI SDK) |
| Валидация email | email-validator |
| Качество | Ruff, mypy, pre-commit, pytest, pytest-asyncio |
| Упаковка | Poetry, Docker |

### AI

- Клиент: официальный **OpenAI Python SDK** (`AsyncOpenAI`)
- Провайдер по умолчанию в примере: **Groq** через `OPENAI_BASE_URL` (протокол совместим с OpenAI)
- Модель в примере: `llama-3.3-70b-versatile`
- Ответ модели: JSON (`response_format: json_object`)

### Frontend

- Jinja2-страница лендинга
- CSS + vanilla JS (`fetch` → `POST /api/contact`)
- Без отдельного SPA-фреймворка — сознательно, чтобы фронт оставался тонким клиентом к тому же API

### Почему такой стек

- **FastAPI** — типизация, Depends, авто-OpenAPI под ТЗ
- **SQLAlchemy 2 + Alembic** — явные миграции и async I/O
- **Файловый rate limit** — без Redis для демо; легко сбросить и понять
- **OpenAI SDK + base_url** — смена провайдера (OpenAI / Groq / OpenRouter) без смены архитектуры
- **Jinja2** уже нужен для писем — тем же стеком отдаётся лендинг

---

## 3. Архитектура

### Структура проекта

```text
StackView/
├── app/
│   ├── api/                 # HTTP: router, dependencies, routers/*
│   ├── core/                # config, exceptions, logging, middleware, ai_prompts
│   ├── db/                  # engine, session, DI сессии
│   ├── models/              # SQLAlchemy ORM
│   ├── repositories/        # доступ к Postgres и JSON rate limit
│   ├── schemas/             # Pydantic DTO
│   ├── services/            # бизнес-логика: contact, ai, email, rate_limit
│   ├── scripts/             # seed
│   ├── static/              # css, js лендинга
│   ├── templates/           # pages/ + email/
│   └── main.py              # FastAPI app, lifespan, static, middleware
├── alembic/                 # миграции
├── tests/
├── scripts/start.sh         # migrate + uvicorn (Docker/Render)
├── Dockerfile
├── render.yaml
└── pyproject.toml
```

### Паттерны

- **Слои:** Controllers (routers) → Services → Repositories
- **DI:** FastAPI `Depends` собирает сервисы и репозитории
- **DTO:** Pydantic-схемы на границе API; ORM-модели внутри persistence
- **Единый формат ошибок:** `ErrorResponse` `{ code, message, details, request_id }`
- **Graceful degradation для AI:** сбой модели не валит приём формы

### Пайплайн обращения

```text
POST /api/contact
  → валидация/санитизация (Pydantic)
  → rate limit по IP (файл)
  → AI enrich (classify ∥ sentiment → suggested_reply)
  → email владельцу + копия пользователю (одна SMTP-сессия)
  → INSERT contact_submissions
  → 201 ContactResponse
```

---

## 4. Реализация API

Базовый префикс API: `/api`. Документация: `/api/docs`.

### Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Лендинг |
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/contact` | Приём обращения |
| `GET` | `/api/metrics` | Агрегаты по БД |

### Примеры

**Health**

```http
GET /api/health
```

```json
{
  "status": "ok",
  "service": "StackView",
  "environment": "development"
}
```

**Contact — успех (201)**

```bash
curl -s -X POST http://127.0.0.1:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Иванов",
    "phone": "+79991234567",
    "email": "ivan@example.com",
    "comment": "Хочу обсудить проект по FastAPI"
  }'
```

Фрагмент ответа:

```json
{
  "status": "accepted",
  "message": "Обращение принято",
  "email_sent": true,
  "ai_available": true,
  "ai_analysis": {
    "category": "collaboration",
    "category_label": "Сотрудничество",
    "sentiment": "positive",
    "sentiment_score": 0.75
  },
  "suggested_reply": "..."
}
```

**Ошибка валидации (422)**

```json
{
  "code": "validation_error",
  "message": "Request validation failed",
  "details": [ { "loc": ["body", "email"], "msg": "..." } ],
  "request_id": null
}
```

**Rate limit (429)** — код `rate_limit_exceeded`.

**Сбой SMTP / БД (502)** — например `email_send_failed`, `email_not_configured`, `database_error`.

### Валидация и ошибки

- Поля формы: длина, `EmailStr`, телефон 10–15 цифр после нормализации
- Санитизация: HTML-теги из `name`/`comment` удаляются, пробелы схлопываются
- Обработчики в `app/core/exception_handlers.py` приводят исключения к `ErrorResponse`
- Ошибки валидации с `ValueError` в контексте Pydantic сериализуются безопасно (без падения JSONResponse)

Статус-коды следуют смыслу REST: **201** создание ресурса-обращения, **422** контракт входа, **429** лимит, **502** внешние зависимости (почта/БД).

---

## 5. AI-интеграция

### Инструменты и задачи

| Функция | Назначение |
|---------|------------|
| `classify_request` | Категория: `job` / `collaboration` / `question` / `other` |
| `analyze_sentiment` | Тональность + score ∈ [-1, 1] |
| `generate_suggested_reply` | Черновик ответа владельцу на русском |

Оркестрация в `AIService.enrich`: сначала параллельно classify + sentiment, затем reply с учётом уже полученного контекста.

### Fallback

- Нет ключа / `AI_ENABLED=false` → обогащение пропускается, форма принимается, `ai_available=false`
- Ошибка или таймаут одной функции → эта функция даёт `None`, остальные продолжают
- `ai_available=true`, если успешна **хотя бы одна** функция
- AI **никогда** не возвращает 502 за счёт модели

Таймаут на вызов: `AI_TIMEOUT_SECONDS` (`asyncio.wait_for`).

### Промпты

Файл: `app/core/ai_prompts.py`.

**Классификация**

```text
Ты классификатор обращений с лендинга разработчика.
Верни JSON с полями category и category_label.
category — одно из: job, collaboration, question, other.
category_label — краткая подпись на русском.
```

**Тональность**

```text
Ты анализатор тональности текста.
Верни JSON с полями sentiment и sentiment_score.
sentiment — одно из: positive, neutral, negative.
sentiment_score — число от -1 до 1.
```

**Черновик ответа**

```text
Ты помощник владельца лендинга разработчика.
Напиши вежливый черновик ответа на обращение на русском языке.
Верни JSON с полем suggested_reply (строка, 2–5 предложений).
Не выдумывай факты, которых нет в сообщении.
```

Метки категорий: `CATEGORY_LABELS` в том же файле.

---

## 6. Что сделано с помощью AI

Проект разрабатывался в связке «разработчик + AI-ассистент (Cursor)».

### Где AI помогал

- Каркас слоёв FastAPI (routers / services / repositories), схемы Pydantic, обработчики ошибок
- Сервисы email (aiosmtplib + Jinja2), AI (`AsyncOpenAI`), rate limit на JSON-файле
- Модель `ContactSubmission`, Alembic-миграция, метрики SQL
- Лендинг (HTML/CSS/JS) по визуальному референсу
- Docker / `render.yaml` / поддержка `DATABASE_URL` и `PORT`
- Черновики тестов pytest и текст README

### Типичные промпты (смысл)

- «Собери ContactService: rate limit → AI → email → БД, AI не должен давать 502»
- «Три AI-функции с независимым fallback и JSON response_format»
- «Лендинг в тёмном стиле референса + форма на `/api/contact`»
- «Подготовь деплой на Render Free + Postgres»

### Что правилось вручную / по фактам эксплуатации

- Политика SMTP: оба письма в одной сессии; в production без SMTP — 502
- Сериализация 422 при `ValueError` в валидаторе телефона
- Переключение AI на Groq (`OPENAI_BASE_URL`) из‑за квоты OpenAI
- Выяснение блокировки SMTP на Render Free и фиксация этого в README
- Настройка Yandex (465 + SSL), seed-данные, нюансы Poetry scripts на Windows
- Точечный рефакторинг типов, докстрингов и конфигов под реальный `.env`

Итоговая ответственность за архитектуру, контракты API и проверку поведения — на авторе репозитория.

---

## 7. Хранение данных

| Данные | Где | Как |
|--------|-----|-----|
| Обращения и поля AI | PostgreSQL `contact_submissions` | SQLAlchemy async, миграции Alembic |
| Статистика | PostgreSQL | `GET /api/metrics` — агрегаты COUNT / GROUP BY |
| Rate limit | файл `data/rate_limit.json` | fixed window по IP, атомарная перезапись |
| Логи приложения | `logs/app.log` | rotating file + console |
| Логи HTTP | `logs/requests.log` | middleware, `X-Request-ID` |

Логи и rate limit намеренно файловые: проще отладка демо без Redis/ELK. Персистентность бизнес-данных — в Postgres (в т.ч. на Render).

---

## Frontend

- Страница: `app/templates/pages/landing.html`
- Стили: `app/static/css/landing.css` (тёмная тема, акцент coral, шрифты Sora / Outfit)
- Логика формы: `app/static/js/contact.js` — JSON на `/api/contact`, подсветка полей при 422, сообщения при 429/502/сети
- UX: одна композиция (hero → фокус → стек → форма), статусы отправки без перезагрузки страницы

---

## Деплой (Render)

В репозитории: `Dockerfile`, `scripts/start.sh` (сначала `alembic upgrade head`, затем uvicorn), `render.yaml`.

Публичный инстанс: **https://stackview-api.onrender.com**

Ограничение Free: исходящий SMTP недоступен — для проверки писем используйте **локальный запуск** с настроенным Yandex.

---

## Лицензия / автор

**Выполнено в рамках тестового задания**

Надежда Попова

Python Developer

📧 nadezhdapopova13@yandex.ru

🔗 GitHub: simbarilion

