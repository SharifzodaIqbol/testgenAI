"""
Pydantic-схемы для валидации запросов и ответов.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.base import TaskStatus, TestCasePriority, TestCaseType


# ── Auth ───────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Projects ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Documents ──────────────────────────────────────────────────────────────────

class DocumentRead(BaseModel):
    id: int
    project_id: int
    filename: str
    content_type: str
    token_count: int
    uploaded_at: datetime
    model_config = {"from_attributes": True}


# ── Generation ─────────────────────────────────────────────────────────────────

class GenerationRequest(BaseModel):
    document_id: int
    num_cases: int = Field(default=10, ge=1, le=50)
    case_types: List[TestCaseType] = Field(
        default=[TestCaseType.FUNCTIONAL, TestCaseType.NEGATIVE]
    )
    focus_area: str = Field(default="", max_length=500)
    language: str = Field(default="ru", pattern="^(ru|en)$")
    suite_name: Optional[str] = Field(default=None, max_length=255)


class GenerationTaskRead(BaseModel):
    id: int
    celery_task_id: Optional[str]
    document_id: int
    test_suite_id: Optional[int]
    status: TaskStatus
    num_cases: int
    progress: int
    error_message: Optional[str]
    llm_prompt_tokens: int
    llm_completion_tokens: int
    created_at: datetime
    completed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Test Cases ─────────────────────────────────────────────────────────────────

class TestStep(BaseModel):
    step: str
    expected: str


class TestCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    preconditions: str = ""
    steps: List[TestStep] = Field(default_factory=list)
    expected_result: str = ""
    priority: TestCasePriority = TestCasePriority.MEDIUM
    case_type: TestCaseType = TestCaseType.FUNCTIONAL
    tags: List[str] = Field(default_factory=list)


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[TestStep]] = None
    expected_result: Optional[str] = None
    priority: Optional[TestCasePriority] = None
    case_type: Optional[TestCaseType] = None
    tags: Optional[List[str]] = None


class TestCaseRead(BaseModel):
    id: int
    suite_id: int
    title: str
    description: str
    preconditions: str
    steps: List[dict]
    expected_result: str
    priority: TestCasePriority
    case_type: TestCaseType
    tags: List[str]
    confidence_score: float
    created_at: datetime
    model_config = {"from_attributes": True}


class TestSuiteRead(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    created_at: datetime
    test_cases: List[TestCaseRead] = []
    model_config = {"from_attributes": True}
