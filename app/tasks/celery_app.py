"""
Celery-приложение и задача асинхронной генерации тест-кейсов.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from celery import Celery

from app.core.config import settings

from app.db.session import engine, AsyncSessionLocal

logger = logging.getLogger(__name__)

celery_app = Celery(
    "testgen",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="tasks.generate_test_cases", max_retries=3)
def run_generation(
    self,
    task_id: int,
    document_id: int,
    num_cases: int,
    case_types: list[str],
    focus_area: str,
    language: str,
    suite_name: str,
) -> dict:
    """
    Основная Celery-задача генерации тест-кейсов.
    Запускает асинхронный код через asyncio.run().
    """

    try:
        engine.pool.dispose()
    except Exception as e:
        logger.warning("Failed to dispose SQLAlchemy pool: %s", e)

    return asyncio.run(_async_generate(
        self, task_id, document_id, num_cases,
        case_types, focus_area, language, suite_name
    ))


async def _async_generate(
    celery_task,
    task_id: int,
    document_id: int,
    num_cases: int,
    case_types: list[str],
    focus_area: str,
    language: str,
    suite_name: str,
) -> dict:
    from app.db.base import (
        GenerationTask, Document, TestSuite, TestCase,
        TaskStatus, TestCasePriority, TestCaseType,
    )
    from app.services.llm_service import generate_test_cases
    from app.services.storage_service import download_file
    from sqlalchemy import select

    current_loop = asyncio.get_running_loop()
    engine.pool._loop = current_loop

    async with AsyncSessionLocal() as db:
        task = await db.get(GenerationTask, task_id)
        if not task:
            logger.error("GenerationTask %d not found", task_id)
            return {"error": "task not found"}

        task.status = TaskStatus.PROCESSING
        task.celery_task_id = celery_task.request.id
        await db.commit()

        try:
            # 2. Получаем документ
            doc = await db.get(Document, document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            # 3. Обновляем прогресс
            task.progress = 10
            await db.commit()

            # 4. Вызываем LLM
            parsed_types = [TestCaseType(t) for t in case_types]
            result = await generate_test_cases(
                doc_text=doc.extracted_text,
                num_cases=num_cases,
                case_types=parsed_types,
                focus_area=focus_area,
                language=language,
            )

            task.progress = 70
            task.llm_prompt_tokens = result["usage"]["prompt_tokens"]
            task.llm_completion_tokens = result["usage"]["completion_tokens"]
            await db.commit()

            # 5. Создаём TestSuite
            suite = TestSuite(
                project_id=doc.project_id,
                name=suite_name or f"Suite — {doc.filename}",
                description=f"Сгенерировано из: {doc.filename}",
            )
            db.add(suite)
            await db.flush()  # получаем suite.id

            task.test_suite_id = suite.id
            await db.commit()

            # 6. Сохраняем TestCase-ы
            for tc_data in result["test_cases"]:
                tc = TestCase(
                    suite_id=suite.id,
                    title=tc_data["title"],
                    description=tc_data["description"],
                    preconditions=tc_data["preconditions"],
                    steps=tc_data["steps"],
                    expected_result=tc_data["expected_result"],
                    priority=TestCasePriority(tc_data["priority"]),
                    case_type=TestCaseType(tc_data["case_type"]),
                    tags=tc_data["tags"],
                    confidence_score=tc_data["confidence_score"],
                )
                db.add(tc)

            # 7. Финализируем
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "Generation task %d completed: %d test cases in suite %d",
                task_id, len(result["test_cases"]), suite.id,
            )
            return {"suite_id": suite.id, "test_cases_count": len(result["test_cases"])}

        except Exception as exc:
            logger.exception("Generation task %d failed", task_id)
            # Пересоздаем сессию исключительно для записи ошибки, если прошлая упала
            try:
                async with AsyncSessionLocal() as fail_db:
                    fail_task = await fail_db.get(GenerationTask, task_id)
                    if fail_task:
                        fail_task.status = TaskStatus.FAILED
                        fail_task.error_message = str(exc)[:2000]
                        await fail_db.commit()
            except Exception as db_err:
                logger.error("Failed to write error status to DB: %s", db_err)
                
            raise celery_task.retry(exc=exc, countdown=30)