from fastapi import APIRouter
from app.api.ai.agents.academic.router import router as academic_router 
from app.api.ai.agents.multilingual.router import router as multilingual_router
from app.api.ai.agents.interview.router import router as interview_router
from app.api.ai.agents.performance.router import router as performance_router

ai_router = APIRouter()

ai_router.include_router(academic_router,prefix="/academic",tags=["Academic Agent"])
ai_router.include_router(multilingual_router,prefix="/multilingual",tags=["Multilingual Agent"])
ai_router.include_router(interview_router,prefix="/interview",tags=["Interview Agent"])
ai_router.include_router(performance_router,prefix="/performance",tags=["Performance Agent"])