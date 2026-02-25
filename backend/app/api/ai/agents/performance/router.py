from fastapi import APIRouter
from app.api.ai.agents.performance.schema import PerformanceAnalysisResponse , PerformanceAnalysisRequest
from app.api.ai.agents.performance.service import prepare_dataframe , classify_students

router = APIRouter()

@router.get("/")
async def test_performance():
    return {"message":"performance agent working"}

@router.post("/analyze",response_model=PerformanceAnalysisResponse)
def analyze_performance(request:PerformanceAnalysisRequest):
    df = prepare_dataframe(request.marks_data)
    
    top,weak,dropout,avg = classify_students(df)

    return PerformanceAnalysisResponse(
        top_students=top.to_dict("records"),
        weak_students=weak.to_dict("records"),
        average_performance=round(avg,2),
        dropout_rist_students=dropout.to_dict("records")
    )

