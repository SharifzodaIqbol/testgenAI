from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

from app.core.security import get_current_user_id
from app.db.base import Document, GenerationTask, Project, TaskStatus
from app.db.session import get_db, AsyncSessionLocal
from app.schemas import GenerationRequest, GenerationTaskRead
from app.tasks.celery_app import run_generation

router = APIRouter()


@router.post("/start", response_model=GenerationTaskRead, status_code=202)
async def start_generation(
    body: GenerationRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Проверяем документ
    doc = await db.get(Document, body.document_id)
    if not doc:
        raise HTTPException(404, "Документ не найден")

    project = await db.get(Project, doc.project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(403, "Нет прав")

    if not doc.extracted_text.strip():
        raise HTTPException(400, "Документ не содержит текста для анализа")

    # Создаём задачу в БД
    task = GenerationTask(
        document_id=body.document_id,
        num_cases=body.num_cases,
        case_types=[t.value for t in body.case_types],
        focus_area=body.focus_area,
        language=body.language,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.flush()

    # Запускаем Celery
    celery_task = run_generation.delay(
        task_id=task.id,
        document_id=body.document_id,
        num_cases=body.num_cases,
        case_types=[t.value for t in body.case_types],
        focus_area=body.focus_area,
        language=body.language,
        suite_name=body.suite_name or f"Suite — {doc.filename}",
    )
    task.celery_task_id = celery_task.id
    await db.commit()

    return task


@router.get("/{task_id}", response_model=GenerationTaskRead)
async def get_task_status(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(404, "Задача не найдена")

    # Проверка прав через документ
    doc = await db.get(Document, task.document_id)
    project = await db.get(Project, doc.project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(403, "Нет прав")

    return task


@router.websocket("/ws/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: int):
    """
    WebSocket для real-time отслеживания прогресса генерации.
    Отправляет JSON с полями: status, progress, suite_id.
    """
    await websocket.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                task = await db.get(GenerationTask, task_id)
                if not task:
                    await websocket.send_text(json.dumps({"error": "task not found"}))
                    break

                data = {
                    "status": task.status.value,
                    "progress": task.progress,
                    "suite_id": task.test_suite_id,
                    "error": task.error_message,
                }
                await websocket.send_text(json.dumps(data))

                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    break

            await asyncio.sleep(2)  # Пуллинг каждые 2 секунды
    except WebSocketDisconnect:
        pass
