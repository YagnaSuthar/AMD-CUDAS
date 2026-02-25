from pydantic import BaseModel
from typing import List,Optional

class SubjectMark(BaseModel):
    subject_id:str
    marks:float
    max_marks:float

class StudentMark(BaseModel):
    student_id:str
    student_name:str
    attendance_percentage:float
    subjects:List[SubjectMark]

class PerformanceAnalysisRequest(BaseModel):
    department_id:str
    semester:int
    marks_data:List[StudentMark]


#Response Schemas

class StudentPerformanceSummary(BaseModel):
    student_id:str
    student_name:str
    average_score:float
    attendance_percentage:float

class PerformanceAnalysisResponse(BaseModel):
    top_students:List[StudentPerformanceSummary]
    weak_students:List[StudentPerformanceSummary]
    average_performance:float
    dropout_rist_students:List[StudentPerformanceSummary]