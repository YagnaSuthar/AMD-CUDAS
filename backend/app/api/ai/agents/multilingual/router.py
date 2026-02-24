from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def test_multilingual():
    return {"message":"multilingual agent working"}