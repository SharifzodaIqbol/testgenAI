"""
Все ORM-модели проекта.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Float, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TestCasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestCaseType(str, enum.Enum):
    FUNCTIONAL = "functional"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    PERFORMANCE = "performance"
    SECURITY = "security"


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped["User"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_suites: Mapped[list["TestSuite"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)   # MinIO object key
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)  # application/pdf, text/markdown
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="documents")
    generation_tasks: Mapped[list["GenerationTask"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    test_suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    # Параметры генерации
    num_cases: Mapped[int] = mapped_column(Integer, default=10)
    case_types: Mapped[list] = mapped_column(JSON, default=list)
    focus_area: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(10), default="ru")
    # Прогресс и результат
    progress: Mapped[int] = mapped_column(Integer, default=0)      # 0-100
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    llm_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="generation_tasks")
    test_suite: Mapped["TestSuite"] = relationship(back_populates="generation_task")


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="test_suites")
    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="suite", cascade="all, delete-orphan")
    generation_task: Mapped["GenerationTask"] = relationship(back_populates="test_suite", uselist=False)


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    preconditions: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)        # [{step, expected}]
    expected_result: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[TestCasePriority] = mapped_column(Enum(TestCasePriority), default=TestCasePriority.MEDIUM)
    case_type: Mapped[TestCaseType] = mapped_column(Enum(TestCaseType), default=TestCaseType.FUNCTIONAL)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0-1.0, оценка LLM
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    suite: Mapped["TestSuite"] = relationship(back_populates="test_cases")
