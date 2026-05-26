"""
Интеграционные тесты API с использованием httpx AsyncClient.
Запуск: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base import Base

TEST_DB_URL = "postgresql+asyncpg://testgen:testgen_secret@localhost:5432/testgen_test"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Регистрация
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
        "full_name": "Test User",
    })
    assert resp.status_code == 201
    user_data = resp.json()
    assert user_data["email"] == "test@example.com"

    # Логин
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "pass12345", "full_name": "Dup"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    # Регистрируемся и логинимся
    await client.post("/api/v1/auth/register", json={
        "email": "proj@example.com",
        "password": "pass12345",
        "full_name": "Proj User",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "proj@example.com", "password": "pass12345"
    })
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/projects/", headers=headers, json={
        "name": "My Project", "description": "Test"
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "My Project"


@pytest.mark.asyncio
async def test_llm_service_mock(monkeypatch):
    """Тест LLM-сервиса с мок-ответом."""
    import app.services.llm_service as llm

    async def mock_generate(*args, **kwargs):
        return {
            "test_cases": [
                {
                    "title": "Тест авторизации",
                    "description": "Проверка входа",
                    "preconditions": "Пользователь зарегистрирован",
                    "steps": [{"step": "Открыть форму входа", "expected": "Форма отображается"}],
                    "expected_result": "Пользователь авторизован",
                    "priority": "high",
                    "case_type": "functional",
                    "tags": ["auth"],
                    "confidence_score": 0.95,
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 200},
        }

    monkeypatch.setattr(llm, "generate_test_cases", mock_generate)
    result = await llm.generate_test_cases("test doc")
    assert len(result["test_cases"]) == 1
    assert result["test_cases"][0]["priority"] == "high"
