from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def test_academic():
    return {"message":"Academic agent working"}