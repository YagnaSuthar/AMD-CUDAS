from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def test_interview():
    return {"message":"interview agent working"}