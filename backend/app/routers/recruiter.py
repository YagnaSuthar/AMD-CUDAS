from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker
from app.models.auth import (
    ApprovalStatus,
    AuthUser,
    Certificate,
    College,
    Department,
    InternalMarks,
)
from app.models.interview import InterviewReport, InterviewSession
from app.models.pipeline import InterviewPipeline
from app.models.job import Job
from app.schemas.recruiter import (
    RecruiterCollegeResponse,
    RecruiterDepartmentResponse,
    RecruiterStudentListEntry,
    RecruiterStudentInterviewSummary,
    RecruiterStudentPipelineSummary,
    RecruiterStudentProfileResponse,
)

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

recruiter_only = RoleChecker(["RECRUITER"])


@router.get("/colleges", response_model=list[RecruiterCollegeResponse])
async def list_colleges(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot access recruiter dashboard")

    result = await db.execute(
        select(College, AuthUser)
        .join(AuthUser, College.principal_id == AuthUser.id)
        .where(College.status == ApprovalStatus.APPROVED)
        .order_by(College.created_at.desc())
    )

    rows = result.all()
    return [
        RecruiterCollegeResponse(
            id=str(col.id),
            name=col.name,
            principal_id=str(col.principal_id),
            principal_name=principal.name,
        )
        for col, principal in rows
    ]


@router.get("/colleges/{college_id}/departments", response_model=list[RecruiterDepartmentResponse])
async def list_college_departments(
    college_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot access recruiter dashboard")

    college_res = await db.execute(select(College).where(College.id == college_id))
    college = college_res.scalar_one_or_none()
    if college is None:
        raise HTTPException(status_code=404, detail="College not found")

    # Department table is owned by principal id
    res = await db.execute(
        select(Department).where(Department.college_principal_id == college.principal_id)
    )
    depts = list(res.scalars().all())
    return [RecruiterDepartmentResponse(id=str(d.id), name=d.name) for d in depts]


@router.get("/students", response_model=list[RecruiterStudentListEntry])
async def list_students(
    college_principal_id: str,
    department: str | None = None,
    semester: int | None = None,
    min_avg_marks: float | None = None,
    min_points: int | None = None,
    skill: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot access recruiter dashboard")

    # Marks subquery: avg% per student; max semester
    marks_q = select(
        InternalMarks.student_id.label("student_id"),
        func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks).label("avg_marks"),
        func.max(InternalMarks.semester).label("marks_semester"),
    ).group_by(InternalMarks.student_id)

    if semester is not None:
        marks_q = marks_q.where(InternalMarks.semester == semester)

    marks_sq = marks_q.subquery("marks_sq")

    cert_sq = (
        select(
            Certificate.student_id.label("student_id"),
            func.coalesce(func.sum(Certificate.points), 0).label("cert_points"),
        )
        .group_by(Certificate.student_id)
        .subquery("cert_sq")
    )

    # Students under this principal
    query = (
        select(
            AuthUser.id,
            AuthUser.name,
            AuthUser.email,
            AuthUser.department,
            func.coalesce(AuthUser.semester, marks_sq.c.marks_semester).label("semester"),
            func.coalesce(marks_sq.c.avg_marks, 0).label("avg_marks"),
            func.coalesce(cert_sq.c.cert_points, 0).label("cert_points"),
            AuthUser.skills,
            AuthUser.resume_url,
        )
        .outerjoin(marks_sq, AuthUser.id == marks_sq.c.student_id)
        .outerjoin(cert_sq, AuthUser.id == cert_sq.c.student_id)
        .where(AuthUser.role == "STUDENT")
    )

    # Limit to the college: recursive CTE that walks each student's parent chain upward.
    # It produces rows (sid, parent_id) for all ancestors; if any parent_id equals the
    # principal_id, that student belongs to the college.
    chain = (
        select(AuthUser.id.label("sid"), AuthUser.parent_id.label("parent_id"))
        .where(AuthUser.role == "STUDENT")
        .cte("chain", recursive=True)
    )

    parent = AuthUser.__table__.alias("parent")
    chain = chain.union_all(
        select(chain.c.sid, parent.c.parent_id)
        .select_from(parent)
        .where(parent.c.id == chain.c.parent_id)
    )

    query = query.where(
        AuthUser.id.in_(
            select(chain.c.sid).where(chain.c.parent_id == college_principal_id)
        )
    )

    if department:
        query = query.where(AuthUser.department == department)

    if semester is not None:
        query = query.where(
            or_(AuthUser.semester == semester, marks_sq.c.marks_semester == semester)
        )

    if min_avg_marks is not None:
        query = query.where(func.coalesce(marks_sq.c.avg_marks, 0) >= min_avg_marks)

    if min_points is not None:
        query = query.where(func.coalesce(cert_sq.c.cert_points, 0) >= min_points)

    if skill:
        query = query.where(func.lower(cast(AuthUser.skills, String)).like(f"%{skill.lower()}%"))

    # Latest semesters first, then high total score
    total_score = (func.coalesce(marks_sq.c.avg_marks, 0) + func.coalesce(cert_sq.c.cert_points, 0)).label("total_score")
    query = query.order_by(func.coalesce(AuthUser.semester, marks_sq.c.marks_semester).desc(), total_score.desc())

    res = await db.execute(query)
    rows = res.all()

    out: list[RecruiterStudentListEntry] = []
    for r in rows:
        avg = float(r.avg_marks or 0)
        pts = int(r.cert_points or 0)
        total = avg + pts
        out.append(
            RecruiterStudentListEntry(
                id=str(r.id),
                name=r.name,
                email=r.email,
                department=r.department,
                semester=r.semester,
                average_marks=round(avg, 2),
                certificate_points=pts,
                total_score=round(total, 2),
                skills=list(r.skills) if r.skills else None,
                resume_url=r.resume_url,
            )
        )

    return out


@router.get("/dashboard")
async def get_recruiter_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    """Get recruiter dashboard statistics including interview performance data."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot access recruiter dashboard")

    recruiter_id = current_user.id

    # Get all pipelines for this recruiter
    pipeline_result = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.recruiter_id == recruiter_id)
        .order_by(InterviewPipeline.updated_at.desc())
    )
    pipelines = list(pipeline_result.scalars().all())

    # Count by status
    status_counts = {}
    for pipeline in pipelines:
        status = pipeline.status.value if hasattr(pipeline.status, "value") else str(pipeline.status)
        status_counts[status] = status_counts.get(status, 0) + 1

    # Get AI interview sessions with scores
    import logging
    logger = logging.getLogger(__name__)
    logger.info("recruiter_dashboard: building interview data for recruiter %s", current_user.id)

    # Simplify: fetch all sessions for this recruiter's pipelines
    ai_session_ids = [p.ai_session_id for p in pipelines if p.ai_session_id]
    interview_data = []
    if ai_session_ids:
        logger.info("recruiter_dashboard: fetching sessions for ai_session_ids=%s", ai_session_ids)
        session_result = await db.execute(
            select(InterviewSession, InterviewReport, InterviewPipeline, AuthUser)
            .join(InterviewReport, InterviewSession.session_id == InterviewReport.session_id, isouter=True)
            .join(InterviewPipeline, InterviewSession.session_id == InterviewPipeline.ai_session_id, isouter=True)
            .join(AuthUser, InterviewSession.student_id == AuthUser.id)
            .where(InterviewSession.session_id.in_(ai_session_ids))
            .order_by(InterviewSession.start_time.desc())
        )
        for session, report, pipeline, student in session_result:
            interview_data.append({
                "session_id": str(session.session_id),
                "student_name": student.name,
                "student_email": student.email,
                "student_department": student.department,
                "job_role": session.job_role,
                "status": session.status.value if hasattr(session.status, "value") else str(session.status),
                "started_at": session.start_time.isoformat() if session.start_time else None,
                "ended_at": session.end_time.isoformat() if session.end_time else None,
                "final_score": float(report.final_score) if report else None,
                "communication_score": float(report.communication_score) if report else None,
                "recommendation": report.recommendation if report else None,
                "pipeline_status": pipeline.status.value if pipeline else None,
                "pipeline_id": str(pipeline.id) if pipeline else None,
                "ai_session_id": str(session.session_id),  # Ensure frontend can fetch report
                "strengths": report.strengths if report else [],
                "weaknesses": report.weaknesses if report else [],
            })
    else:
        logger.info("recruiter_dashboard: no ai_session_ids found for recruiter's pipelines")

    # Calculate statistics
    total_interviews = len(interview_data)
    completed_interviews = len([i for i in interview_data if i["status"] == "completed"])
    average_score = 0
    if completed_interviews > 0:
        scores = [i["final_score"] for i in interview_data if i["final_score"] is not None]
        average_score = sum(scores) / len(scores) if scores else 0

    # Get recent activity (last 10)
    recent_activity = interview_data[:10]

    return {
        "statistics": {
            "total_assigned": len(pipelines),
            "ai_completed": status_counts.get("AI_COMPLETED", 0),
            "round2_invited": status_counts.get("ROUND2_INVITED", 0),
            "round2_completed": status_counts.get("ROUND2_COMPLETED", 0),
            "hired": status_counts.get("HIRED", 0),
            "total_interviews": total_interviews,
            "completed_interviews": completed_interviews,
            "average_score": round(average_score, 2),
        },
        "recent_interviews": recent_activity,
        "status_breakdown": status_counts,
    }


@router.get("/student/{student_id}", response_model=RecruiterStudentProfileResponse)
async def get_student_profile(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(recruiter_only),
):
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot access recruiter dashboard")

    u_res = await db.execute(select(AuthUser).where(AuthUser.id == student_id, AuthUser.role == "STUDENT"))
    student = u_res.scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    # Interviews (latest first)
    s_res = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.student_id == student.id)
        .order_by(InterviewSession.start_time.desc())
        .limit(10)
    )
    sessions = list(s_res.scalars().all())

    summaries: list[RecruiterStudentInterviewSummary] = []
    if sessions:
        session_ids = [s.session_id for s in sessions]
        rpt_res = await db.execute(
            select(InterviewReport).where(InterviewReport.session_id.in_(session_ids))
        )
        reports = {r.session_id: r for r in rpt_res.scalars().all()}

        for s in sessions:
            rpt = reports.get(s.session_id)
            summaries.append(
                RecruiterStudentInterviewSummary(
                    session_id=str(s.session_id),
                    job_role=s.job_role,
                    status=s.status.value if hasattr(s.status, "value") else str(s.status),
                    started_at=s.start_time.isoformat() if s.start_time else "",
                    ended_at=s.end_time.isoformat() if s.end_time else None,
                    final_score=float(rpt.final_score) if rpt else None,
                    recommendation=rpt.recommendation if rpt else None,
                )
            )

    # Pipelines for this student
    p_res = await db.execute(
        select(InterviewPipeline)
        .where(InterviewPipeline.student_id == student.id)
        .order_by(InterviewPipeline.updated_at.desc())
        .limit(20)
    )
    pipelines = list(p_res.scalars().all())
    p_out: list[RecruiterStudentPipelineSummary] = []
    for p in pipelines:
        p_out.append(
            RecruiterStudentPipelineSummary(
                pipeline_id=str(p.id),
                job_id=str(p.job_id),
                status=p.status.value if hasattr(p.status, "value") else str(p.status),
                ai_session_id=str(p.ai_session_id) if p.ai_session_id else None,
                round2_link=p.round2_link,
                hired_company_name=p.hired_company_name,
                updated_at=p.updated_at.isoformat() if p.updated_at else "",
            )
        )

    return RecruiterStudentProfileResponse(
        id=str(student.id),
        name=student.name,
        email=student.email,
        department=student.department,
        semester=student.semester,
        skills=list(student.skills) if student.skills else None,
        resume_url=student.resume_url,
        interviews=summaries,
        pipelines=p_out,
    )
