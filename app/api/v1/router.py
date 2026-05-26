from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, documents, generation, test_cases

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["test-cases"])
