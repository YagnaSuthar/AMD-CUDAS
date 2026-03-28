import pandas as pd 

def prepare_dataframe(marks_data):
    rows =[]

    for student in marks_data:
        total_marks= 0 
        total_max = 0

        for subject in student.subjects:
            total_marks += subject.marks
            total_max += subject.max_marks

        avg_score = (total_marks / total_max) * 100 if total_max else 0.0

        rows.append({
            "student_id": student.student_id,
            "student_name": student.student_name,
            "average_score": avg_score,
            "attendance_percentage": student.attendance_percentage,
        })
    return pd.DataFrame(rows)


def classify_students(df):

    #Top Students 
    top_students = df[df["average_score"] >= 85]

    #Weak Students
    weak_students = df[df["average_score"] < 50]

    #Dropout risk logic 
    dropout_risk = df[
        (df["average_score"] < 50) & (df["attendance_percentage"] < 60)

    ]

    overall_avg = df["average_score"].mean()

    return top_students,weak_students,dropout_risk,overall_avg