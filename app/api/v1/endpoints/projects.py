from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.base import Project
from app.db.session import get_db
from app.schemas import ProjectCreate, ProjectRead

router = APIRouter()


@router.get("/", response_model=List[ProjectRead])
async def list_projects(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(
        select(Project).where(Project.owner_id == user_id).order_by(Project.created_at.desc())
    )
    return result.all()


@router.post("/", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    project = Project(name=body.name, description=body.description, owner_id=user_id)
    db.add(project)
    await db.flush()
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_owned(project_id, user_id, db)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_owned(project_id, user_id, db)
    await db.delete(project)


async def _get_owned(project_id: int, user_id: int, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project or project.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project
