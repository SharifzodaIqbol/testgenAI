from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.base import Document, Project
from app.db.session import get_db
from app.schemas import DocumentRead
from app.services.document_service import estimate_tokens, extract_text
from app.services.storage_service import delete_file, upload_file

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/markdown",
    "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Проверка прав
    project = await db.get(Project, project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(404, "Проект не найден")

    # Проверка типа
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            415,
            f"Неподдерживаемый тип файла: {content_type}. "
            f"Разрешены: PDF, DOCX, MD, TXT",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Файл слишком большой (максимум 10 МБ)")

    # Сохраняем в MinIO
    storage_key = upload_file(content, file.filename or "document", content_type)

    # Извлекаем текст
    extracted = await extract_text(content, content_type, file.filename or "")
    token_count = estimate_tokens(extracted)

    doc = Document(
        project_id=project_id,
        filename=file.filename or "document",
        storage_key=storage_key,
        content_type=content_type,
        extracted_text=extracted,
        token_count=token_count,
    )
    db.add(doc)
    await db.flush()
    return doc


@router.get("/project/{project_id}", response_model=List[DocumentRead])
async def list_documents(
    project_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(404, "Проект не найден")

    docs = await db.scalars(
        select(Document).where(Document.project_id == project_id)
        .order_by(Document.uploaded_at.desc())
    )
    return docs.all()


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Документ не найден")

    project = await db.get(Project, doc.project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(403, "Нет прав")

    delete_file(doc.storage_key)
    await db.delete(doc)
