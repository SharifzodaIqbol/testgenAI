# TestGen AI — Генерация тест-кейсов с помощью LLM

Полноценная система для автоматической генерации тест-кейсов из технической документации
на основе языковых моделей (Groq / LLaMA 3).

## Стек технологий

| Слой | Технология |
|------|-----------|
| Backend API | **FastAPI** + Python 3.12 |
| База данных | **PostgreSQL 16** + SQLAlchemy (async) |
| Очередь задач | **Celery** + **Redis** |
| LLM | **Groq API** (LLaMA 3 70B) |
| Хранение файлов | **MinIO** (S3-совместимый) |
| Миграции | **Alembic** |
| Парсинг документов | pdfplumber, python-docx |
| Frontend | **React** + Vite + React Query |
| Мониторинг задач | **Flower** (Celery dashboard) |
| Контейнеризация | **Docker** + Docker Compose |
| Аутентификация | **JWT** (access + refresh токены) |
| Экспорт | JSON, **Excel** (openpyxl) |

## Архитектура

```
Frontend (React) ──► FastAPI ──► PostgreSQL
                         │
                         ├──► Celery Worker ──► Groq API (LLaMA 3)
                         │         │
                         └──► Redis (queue + cache)
                         │
                         └──► MinIO (document storage)
```

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <your-repo>
cd testgen

# Скопируй и заполни переменные окружения
cp .env.example .env
# Вставь свой GROQ_API_KEY в .env
# Получи ключ на: https://console.groq.com
```

### 2. Запуск через Docker Compose

```bash
docker-compose up -d --build
```

Сервисы после запуска:
- API + Swagger UI: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Flower (Celery monitor): http://localhost:5555
- MinIO Console: http://localhost:9001

### 3. Миграции базы данных

```bash
# Создать миграцию
docker-compose exec api alembic revision --autogenerate -m "initial"

# Применить миграции
docker-compose exec api alembic upgrade head
```

### 4. Запуск тестов

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## API Endpoints

### Аутентификация
```
POST /api/v1/auth/register   — регистрация
POST /api/v1/auth/login      — вход (получение JWT)
POST /api/v1/auth/refresh    — обновление токена
GET  /api/v1/auth/me         — текущий пользователь
```

### Проекты
```
GET    /api/v1/projects/          — список проектов
POST   /api/v1/projects/          — создать проект
GET    /api/v1/projects/{id}      — детали проекта
DELETE /api/v1/projects/{id}      — удалить проект
```

### Документы
```
POST   /api/v1/documents/upload?project_id=N   — загрузить файл (PDF/DOCX/MD/TXT)
GET    /api/v1/documents/project/{project_id}  — список документов
DELETE /api/v1/documents/{id}                  — удалить документ
```

### Генерация
```
POST /api/v1/generation/start        — запустить генерацию (возвращает task_id)
GET  /api/v1/generation/{task_id}    — статус задачи (polling)
WS   /api/v1/generation/ws/{task_id} — WebSocket live-прогресс
```

### Тест-кейсы
```
GET    /api/v1/test-cases/suites/project/{id}   — все suite проекта
GET    /api/v1/test-cases/suites/{suite_id}     — suite с тест-кейсами
DELETE /api/v1/test-cases/suites/{suite_id}     — удалить suite
POST   /api/v1/test-cases/suites/{id}/cases     — добавить тест-кейс вручную
PATCH  /api/v1/test-cases/{case_id}             — редактировать тест-кейс
DELETE /api/v1/test-cases/{case_id}             — удалить тест-кейс

GET /api/v1/test-cases/suites/{id}/export/json  — экспорт в JSON
GET /api/v1/test-cases/suites/{id}/export/excel — экспорт в Excel
```

## Пример запроса

### 1. Логин
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "mypassword"}'
```

### 2. Загрузка документа
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload?project_id=1" \
  -H "Authorization: Bearer <token>" \
  -F "file=@requirements.pdf"
```

### 3. Запуск генерации
```bash
curl -X POST http://localhost:8000/api/v1/generation/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "num_cases": 15,
    "case_types": ["functional", "negative", "boundary"],
    "focus_area": "авторизация",
    "language": "ru"
  }'
```

### 4. Проверка статуса
```bash
curl http://localhost:8000/api/v1/generation/1 \
  -H "Authorization: Bearer <token>"
```

## Модель тест-кейса

```json
{
  "id": 1,
  "title": "Авторизация с корректными данными",
  "description": "Проверка успешного входа в систему",
  "preconditions": "Пользователь зарегистрирован в системе",
  "steps": [
    {"step": "Открыть страницу входа", "expected": "Страница отображается"},
    {"step": "Ввести email и пароль", "expected": "Данные введены"},
    {"step": "Нажать кнопку Войти", "expected": "Перенаправление на главную"}
  ],
  "expected_result": "Пользователь авторизован, отображается личный кабинет",
  "priority": "critical",
  "case_type": "functional",
  "tags": ["auth", "login", "smoke"],
  "confidence_score": 0.97
}
```

## Структура проекта

```
testgen/
├── app/
│   ├── api/v1/endpoints/    # FastAPI роуты
│   ├── core/                # Конфиг, безопасность, логирование
│   ├── db/                  # SQLAlchemy модели и сессии
│   ├── schemas/             # Pydantic схемы
│   ├── services/            # Бизнес-логика (LLM, документы, MinIO)
│   ├── tasks/               # Celery задачи
│   └── main.py              # Точка входа FastAPI
├── alembic/                 # Миграции БД
├── frontend/src/            # React приложение
├── tests/                   # Pytest тесты
├── docker/                  # Dockerfiles
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Ключевые особенности

- **Async throughout**: все IO операции асинхронные (asyncpg, httpx, FastAPI)
- **Real-time WebSocket**: live-прогресс генерации без polling
- **Prompt engineering**: структурированные промпты с JSON-output mode
- **Confidence scoring**: LLM оценивает уверенность в каждом тест-кейсе
- **Multi-format export**: JSON и Excel с форматированием
- **Document chunking**: автоматическое обрезание документов под контекстное окно
- **Retry logic**: автоматические повторы Celery при ошибках LLM API
- **JWT auth**: access + refresh токены с раздельными сроками жизни
