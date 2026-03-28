from fastapi import APIRouter
from app.api.ai.router import ai_router
from app.routers.applications import router as applications_router

api_router = APIRouter()

@api_router.get("/",tags=["Welcome to the CUDAS a AI Agents Powered Full Functional Web Application"])
async def home():
    return {"message":"contact Yagna Suthar 9265679968 if you find anything in project structure that not understable!!"}

api_router.include_router(ai_router,prefix="/ai",tags=["AI Based Endpoints"])
api_router.include_router(applications_router)