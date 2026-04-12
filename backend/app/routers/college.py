import uuid
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    RoleChecker, get_current_user,
    principal_or_above, principal_only, hod_only, faculty_only, student_only
)
from app.models.auth import AuthUser, Timetable, InternalMarks, Certificate, Department, MentorAssignment
from app.models.auth import StudentPerformanceCategory, StudentPerformanceCategoryType
from app.schemas.auth import (
    UserResponse, MessageResponse, AddUserRequest,
    TimetableCreate, TimetableUpdate, TimetableResponse,
    MarksUpload, MarksUpdate, MarksResponse, MarksLockRequest,
    CertificateResponse, ProjectResponse,
    PrincipalOverviewResponse, DepartmentDetail,
    HodOverviewResponse, StudentBrief,
    FacultyOverviewResponse, SubjectStat,
    StudentAcademicResponse, StudentMarksDetail,
    DepartmentCreate, DepartmentResponse,
    MentorAssignmentCreate, MentorAssignmentResponse,
    LeaderboardEntry, CareerRoadmapResponse,
)
from app.services.user_service import get_children, can_create_role, get_user_by_email
from app.services.email_service import send_credentials_email, send_reset_password_email
from app.services.certificate_service import (
    create_certificate_and_block,
    save_certificate_file,
    sha256_hex,
)

router = APIRouter(prefix="/college", tags=["College Management"])



CERT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "certificate")


# ══════════════════════════════════════════════════════════════════════════
#  EXISTING ENDPOINTS (preserved)
# ══════════════════════════════════════════════════════════════════════════


# ── List subordinate users ────────────────────────────────────────────────


@router.get("/users", response_model=list[UserResponse])
async def list_my_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List users created by the current user (direct children)."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="CUDAS admin uses /admin routes")

    children = await get_children(db, current_user.id)
    return [
        UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            department=u.department,
            semester=u.semester,
            roll_number=u.roll_number,
            phone_number=u.phone_number,
            parent_id=str(u.parent_id) if u.parent_id else None,
        )
        for u in children
    ]


# ── Delete subordinate user ───────────────────────────────────────────────


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_subordinate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a user that was created by the current user."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="CUDAS admin uses /admin routes")

    # Verify the user is a child of the current user
    result = await db.execute(
        select(AuthUser).where(AuthUser.id == user_id, AuthUser.parent_id == current_user.id)
    )
    user_to_delete = result.scalar_one_or_none()

    if not user_to_delete:
        raise HTTPException(
            status_code=404, detail="User not found or is not your subordinate."
        )

    await db.delete(user_to_delete)
    await db.commit()

    return MessageResponse(message="User deleted successfully.")


@router.get("/all-users", response_model=list[UserResponse])
async def list_all_hierarchy_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(principal_or_above),
):
    """Recursively list all users under the current user's hierarchy."""
    if isinstance(current_user, dict):
        # CUDAS admin — return all users
        result = await db.execute(select(AuthUser))
        users = result.scalars().all()
    else:
        users = await _get_all_descendants(db, current_user.id)

    return [
        UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            department=u.department,
            semester=u.semester,
            roll_number=u.roll_number,
            phone_number=u.phone_number,
            parent_id=str(u.parent_id) if u.parent_id else None,
        )
        for u in users
    ]


async def _get_all_descendants(db: AsyncSession, parent_id) -> list:
    """BFS to get all descendants."""
    all_users = []
    queue = [parent_id]
    while queue:
        pid = queue.pop(0)
        children = await get_children(db, pid)
        for child in children:
            all_users.append(child)
            queue.append(child.id)
    return all_users


# ── Manually Add a Subordinate User ─────────────────────────────────────────


CHILD_ROLE_MAP = {
    "COLLEGE_PRINCIPAL": "HOD",
    "HOD": "FACULTY",
    "FACULTY": "STUDENT",
    "COMPANY_ADMIN": "RECRUITER",
}


@router.post("/add-user", response_model=MessageResponse)
async def add_user_manually(
    body: AddUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually add a subordinate user (e.g. Principal adds an HOD)."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="CUDAS admin uses /admin routes")

    parent_role = current_user.role
    target_role = CHILD_ROLE_MAP.get(parent_role)
    if not target_role:
        raise HTTPException(status_code=403, detail="Your role cannot create subordinate users.")

    # Check if email already exists
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    # Auto-assign department if not provided and parent has one
    final_dept = body.department
    if not final_dept and current_user.department:
        final_dept = current_user.department

    # Generate reset token for new user
    import uuid as uuid_pkg
    reset_token = str(uuid_pkg.uuid4())
    from datetime import datetime, timedelta, timezone
    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    new_user = AuthUser(
        name=body.name,
        email=body.email,
        hashed_password=None,
        role=target_role,
        parent_id=current_user.id,
        is_verified=True,
        department=final_dept,
        must_reset_password=True,
        reset_token=reset_token,
        reset_token_expiry=expiry,
    )
    db.add(new_user)
    await db.flush()
    await db.commit()

    # Send credential email notifying the user to reset password
    try:
        # Construct reset URL for localhost
        # In a real app we'd use settings.FRONTEND_URL, but user specifically asked for localhost link fix
        reset_url = "http://localhost:5173" 
        send_credentials_email(body.email, body.name, reset_token, target_role, reset_url)
    except Exception as e:
        print(f"Email failed: {e}")
        pass  # Don't fail the request if email sending fails

    return MessageResponse(message=f"{target_role} '{body.name}' added successfully. They will receive an email to set their password.")


# ══════════════════════════════════════════════════════════════════════════
#  PRINCIPAL DASHBOARD ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@router.get("/principal/overview", response_model=PrincipalOverviewResponse)
async def principal_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(principal_only),
):
    """College overview: total depts, HODs, faculty, students, performance."""
    all_desc = await _get_all_descendants(db, current_user.id)

    hods = [u for u in all_desc if u.role == "HOD"]
    faculty = [u for u in all_desc if u.role == "FACULTY"]
    students = [u for u in all_desc if u.role == "STUDENT"]

    # Departments = unique departments from HODs
    departments_set = set()
    for h in hods:
        if h.department:
            departments_set.add(h.department)
    # also from faculty & students
    for u in faculty + students:
        if u.department:
            departments_set.add(u.department)

    # Calculate per-department stats
    dept_details = []
    for dept in departments_set:
        dept_students = [s for s in students if s.department == dept]
        dept_faculty = [f for f in faculty if f.department == dept]

        # Average marks from internal_marks table
        student_ids = [s.id for s in dept_students]
        avg = 0.0
        if student_ids:
            result = await db.execute(
                select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
                .where(InternalMarks.student_id.in_(student_ids))
            )
            avg = result.scalar() or 0.0

        dept_details.append(DepartmentDetail(
            department=dept,
            student_count=len(dept_students),
            faculty_count=len(dept_faculty),
            average_marks=round(avg, 2),
        ))

    # Overall performance
    all_student_ids = [s.id for s in students]
    overall = 0.0
    if all_student_ids:
        result = await db.execute(
            select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
            .where(InternalMarks.student_id.in_(all_student_ids))
        )
        overall = result.scalar() or 0.0

    return PrincipalOverviewResponse(
        total_departments=len(departments_set),
        total_hods=len(hods),
        total_faculty=len(faculty),
        total_students=len(students),
        overall_performance=round(overall, 2),
        departments=dept_details,
    )


@router.get("/principal/departments", response_model=list[DepartmentDetail])
async def principal_departments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(principal_only),
):
    """Department-wise summary: avg %, student count, faculty count."""
    all_desc = await _get_all_descendants(db, current_user.id)
    faculty = [u for u in all_desc if u.role == "FACULTY"]
    students = [u for u in all_desc if u.role == "STUDENT"]

    departments_set = set()
    for u in all_desc:
        if u.department:
            departments_set.add(u.department)

    results = []
    for dept in departments_set:
        dept_students = [s for s in students if s.department == dept]
        dept_faculty = [f for f in faculty if f.department == dept]
        student_ids = [s.id for s in dept_students]
        avg = 0.0
        if student_ids:
            r = await db.execute(
                select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
                .where(InternalMarks.student_id.in_(student_ids))
            )
            avg = r.scalar() or 0.0
        results.append(DepartmentDetail(
            department=dept,
            student_count=len(dept_students),
            faculty_count=len(dept_faculty),
            average_marks=round(avg, 2),
        ))
    return results


# ── Department Management ────────────────────────────────────────────────


@router.post("/departments", response_model=MessageResponse)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(principal_only),
):
    """Principal creates a new department name."""
    # Check if already exists for this principal
    res = await db.execute(
        select(Department).where(
            Department.name == body.name,
            Department.college_principal_id == current_user.id
        )
    )
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Department already exists.")

    dept = Department(name=body.name, college_principal_id=current_user.id)
    db.add(dept)
    await db.commit()
    return MessageResponse(message=f"Department '{body.name}' created.")


@router.get("/departments/list", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all departments for the current user's college."""
    # Find principal ID for this user's hierarchy
    principal_id = None
    if current_user.role == "COLLEGE_PRINCIPAL":
        principal_id = current_user.id
    else:
        # Traverse up to find principal or use parent chain
        # For simplicity in this hierarchy: Student -> Faculty -> HOD -> Principal
        # We can find the principal by looking for the ancestor with role COLLEGE_PRINCIPAL
        # or just find the user whose parent_id is None if we assume only one college per DB instance,
        # but better to find the specific principal.
        
        # A quick way: find the principal who is at the top of this user's parent chain
        curr = current_user
        while curr.parent_id:
            res = await db.execute(select(AuthUser).where(AuthUser.id == curr.parent_id))
            curr = res.scalar_one_or_none()
            if not curr: break
            if curr.role == "COLLEGE_PRINCIPAL":
                principal_id = curr.id
                break
    
    if not principal_id:
        return []

    res = await db.execute(select(Department).where(Department.college_principal_id == principal_id))
    depts = res.scalars().all()
    return [DepartmentResponse(id=str(d.id), name=d.name) for d in depts]


# ══════════════════════════════════════════════════════════════════════════
#  HOD DASHBOARD ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@router.get("/hod/overview", response_model=HodOverviewResponse)
async def hod_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Department overview: faculty, students, avg, top/weak students."""
    all_desc = await _get_all_descendants(db, current_user.id)
    faculty = [u for u in all_desc if u.role == "FACULTY"]
    students = [u for u in all_desc if u.role == "STUDENT"]

    # Calculate student averages
    student_avgs = []
    for s in students:
        r = await db.execute(
            select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
            .where(InternalMarks.student_id == s.id)
        )
        avg = r.scalar() or 0.0
        student_avgs.append((s, round(avg, 2)))

    # Sort by average
    student_avgs.sort(key=lambda x: x[1], reverse=True)

    dept_avg = sum(a for _, a in student_avgs) / len(student_avgs) if student_avgs else 0.0

    top_students = [
        StudentBrief(id=str(s.id), name=s.name, email=s.email, department=s.department, average=a)
        for s, a in student_avgs[:10]
    ]
    weak_students = [
        StudentBrief(id=str(s.id), name=s.name, email=s.email, department=s.department, average=a)
        for s, a in student_avgs if a < 40.0
    ]

    return HodOverviewResponse(
        total_faculty=len(faculty),
        total_students=len(students),
        department_average=round(dept_avg, 2),
        top_students=top_students,
        weak_students=weak_students,
    )


# ── HOD Timetable CRUD ──────────────────────────────────────────────────


@router.post("/hod/timetable", response_model=MessageResponse)
async def create_timetable(
    body: TimetableCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Create a timetable entry for the HOD's department. Auto-archives past ones."""
    from datetime import date
    today = date.today().isoformat()
    
    # Auto-archive past exams for this department
    await db.execute(
        update(Timetable)
        .where(
            Timetable.department == (current_user.department or "Unknown"),
            Timetable.status == "active",
            Timetable.exam_date < today
        )
        .values(status="archived")
    )

    tt = Timetable(
        department=current_user.department or "Unknown",
        semester=body.semester,
        subject_name=body.subject_name,
        exam_date=body.exam_date,
        exam_time=body.exam_time,
        created_by=current_user.id,
        status="active"
    )
    db.add(tt)
    await db.commit()
    return MessageResponse(message="Timetable entry created successfully.")


@router.get("/hod/timetable", response_model=list[TimetableResponse])
async def list_timetable_hod(
    status: str = "active",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """List timetable entries for the HOD's department, filtered by status."""
    from datetime import date
    today = date.today().isoformat()
    dept = current_user.department or "Unknown"

    # Auto-archive past exams for this department before listing
    if status == "active":
        await db.execute(
            update(Timetable)
            .where(Timetable.department == dept, Timetable.status == "active", Timetable.exam_date < today)
            .values(status="archived")
        )
        await db.commit()

    result = await db.execute(
        select(Timetable)
        .where(Timetable.department == dept, Timetable.status == status)
        .order_by(Timetable.exam_date)
    )
    entries = result.scalars().all()
    return [
        TimetableResponse(
            id=str(e.id), department=e.department, semester=e.semester,
            subject_name=e.subject_name, exam_date=e.exam_date,
            exam_time=e.exam_time, status=e.status,
            published_at=str(e.published_at) if e.published_at else None,
            created_at=str(e.created_at) if e.created_at else None,
        )
        for e in entries
    ]


@router.put("/hod/timetable/{entry_id}", response_model=MessageResponse)
async def update_timetable(
    entry_id: uuid.UUID,
    body: TimetableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Edit a timetable entry (HOD can only edit own department)."""
    result = await db.execute(
        select(Timetable).where(
            Timetable.id == entry_id,
            Timetable.department == (current_user.department or "Unknown"),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found or access denied.")

    if body.semester is not None:
        entry.semester = body.semester
    if body.subject_name is not None:
        entry.subject_name = body.subject_name
    if body.exam_date is not None:
        entry.exam_date = body.exam_date
    if body.exam_time is not None:
        entry.exam_time = body.exam_time

    await db.commit()
    return MessageResponse(message="Timetable entry updated successfully.")


@router.delete("/hod/timetable/{entry_id}", response_model=MessageResponse)
async def delete_timetable(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Delete a timetable entry (HOD can only delete own department)."""
    result = await db.execute(
        select(Timetable).where(
            Timetable.id == entry_id,
            Timetable.department == (current_user.department or "Unknown"),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found or access denied.")

    await db.delete(entry)
    await db.commit()
    return MessageResponse(message="Timetable entry deleted successfully.")


# ── HOD Marks Monitoring ─────────────────────────────────────────────────


@router.get("/hod/marks", response_model=list[MarksResponse])
async def hod_view_marks(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """View all marks for students under the HOD's hierarchy."""
    all_desc = await _get_all_descendants(db, current_user.id)
    student_ids = [u.id for u in all_desc if u.role == "STUDENT"]

    if not student_ids:
        return []

    result = await db.execute(
        select(InternalMarks, AuthUser.name)
        .join(AuthUser, InternalMarks.student_id == AuthUser.id)
        .where(InternalMarks.student_id.in_(student_ids))
        .order_by(InternalMarks.semester, InternalMarks.subject_name)
    )
    rows = result.all()
    return [
        MarksResponse(
            id=str(m.id), student_id=str(m.student_id), student_name=name,
            subject_name=m.subject_name, semester=m.semester,
            marks_obtained=m.marks_obtained, max_marks=m.max_marks,
            is_locked=m.is_locked, uploaded_by=str(m.uploaded_by),
        )
        for m, name in rows
    ]


@router.put("/hod/marks/lock", response_model=MessageResponse)
async def hod_lock_marks(
    body: MarksLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Lock all marks for a given semester in the HOD's department."""
    all_desc = await _get_all_descendants(db, current_user.id)
    student_ids = [u.id for u in all_desc if u.role == "STUDENT"]

    if not student_ids:
        raise HTTPException(status_code=404, detail="No students found.")

    result = await db.execute(
        select(InternalMarks).where(
            InternalMarks.student_id.in_(student_ids),
            InternalMarks.semester == body.semester,
        )
    )
    marks_list = result.scalars().all()
    for m in marks_list:
        m.is_locked = True
    await db.commit()
    return MessageResponse(message=f"Semester {body.semester} marks locked successfully.")


@router.put("/hod/marks/approve", response_model=MessageResponse)
async def hod_approve_marks(
    body: MarksLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """Approve (finalize) semester results — same as lock (extensible later)."""
    all_desc = await _get_all_descendants(db, current_user.id)
    student_ids = [u.id for u in all_desc if u.role == "STUDENT"]

    if not student_ids:
        raise HTTPException(status_code=404, detail="No students found.")

    result = await db.execute(
        select(InternalMarks).where(
            InternalMarks.student_id.in_(student_ids),
            InternalMarks.semester == body.semester,
        )
    )
    marks_list = result.scalars().all()
    for m in marks_list:
        m.is_locked = True
    await db.commit()
    return MessageResponse(message=f"Semester {body.semester} results approved successfully.")


# ── HOD Mentor Assignment ───────────────────────────────────────────────


@router.post("/hod/assign-mentor", response_model=MessageResponse)
async def assign_mentor(
    body: MentorAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """HOD assigns a faculty as a mentor for a semester."""
    faculty_id = uuid.UUID(body.faculty_id)
    
    # Verify faculty is HOD's subordinate
    res = await db.execute(
        select(AuthUser).where(AuthUser.id == faculty_id, AuthUser.parent_id == current_user.id)
    )
    faculty = res.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=403, detail="Faculty not found in your department.")

    # Check if assignment already exists
    res = await db.execute(
        select(MentorAssignment).where(
            MentorAssignment.faculty_id == faculty_id,
            MentorAssignment.semester == body.semester,
            MentorAssignment.department == (current_user.department or "Unknown")
        )
    )
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This faculty is already assigned as mentor for this semester.")

    assign = MentorAssignment(
        faculty_id=faculty_id,
        semester=body.semester,
        department=current_user.department or "Unknown",
        assigned_by=current_user.id
    )
    db.add(assign)
    await db.commit()
    return MessageResponse(message=f"Mentor assigned for Semester {body.semester}.")


@router.get("/hod/mentors", response_model=list[MentorAssignmentResponse])
async def list_mentors(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(hod_only),
):
    """List all mentor assignments for the HOD's department."""
    res = await db.execute(
        select(MentorAssignment, AuthUser.name)
        .join(AuthUser, MentorAssignment.faculty_id == AuthUser.id)
        .where(MentorAssignment.department == (current_user.department or "Unknown"))
    )
    rows = res.all()
    return [
        MentorAssignmentResponse(
            id=str(m.id),
            faculty_id=str(m.faculty_id),
            faculty_name=name,
            semester=m.semester,
            department=m.department,
            created_at=str(m.created_at)
        )
        for m, name in rows
    ]


@router.get("/mentor/faculty/{faculty_id}", response_model=list[MentorAssignmentResponse])
async def get_faculty_mentors(
    faculty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all mentor assignments for a specific faculty member."""
    res = await db.execute(
        select(MentorAssignment)
        .where(MentorAssignment.faculty_id == faculty_id)
        .order_by(MentorAssignment.semester)
    )
    assignments = res.scalars().all()
    return [
        MentorAssignmentResponse(
            id=str(m.id),
            faculty_id=str(m.faculty_id),
            semester=m.semester,
            department=m.department,
            created_at=str(m.created_at)
        )
        for m in assignments
    ]


# ══════════════════════════════════════════════════════════════════════════
#  FACULTY DASHBOARD ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@router.get("/faculty/overview", response_model=FacultyOverviewResponse)
async def faculty_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(faculty_only),
):
    """Class overview: assigned semesters, subjects, student count per subject."""
    students = await get_children(db, current_user.id)
    student_ids = [s.id for s in students]

    # Get unique semesters & subjects from uploaded marks
    result = await db.execute(
        select(InternalMarks.semester, InternalMarks.subject_name, func.count(InternalMarks.id))
        .where(InternalMarks.uploaded_by == current_user.id)
        .group_by(InternalMarks.semester, InternalMarks.subject_name)
    )
    rows = result.all()

    semesters_from_marks = list(set(r[0] for r in rows))
    subjects = list(set(r[1] for r in rows))

    # Also get semesters explicitly assigned by HOD
    mentor_res = await db.execute(
        select(MentorAssignment.semester)
        .where(MentorAssignment.faculty_id == current_user.id)
    )
    mentor_semesters = mentor_res.scalars().all()

    # Combine and deduplicate
    all_semesters = list(set(semesters_from_marks + mentor_semesters))

    subject_stats = []
    for sem, subj, count in rows:
        # Get avg for this subject
        r = await db.execute(
            select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
            .where(InternalMarks.uploaded_by == current_user.id, InternalMarks.subject_name == subj)
        )
        avg = r.scalar() or 0.0
        subject_stats.append(SubjectStat(subject_name=subj, student_count=count, average_marks=round(avg, 2)))

    # Also get current active timetable for the department
    dept = current_user.department or "Unknown"
    from datetime import date
    today = date.today().isoformat()
    
    # Auto-archive past exams for this department before listing
    await db.execute(
        update(Timetable)
        .where(Timetable.department == dept, Timetable.status == "active", Timetable.exam_date < today)
        .values(status="archived")
    )
    await db.commit()

    tt_res = await db.execute(
        select(Timetable).where(Timetable.department == dept, Timetable.status == "active").order_by(Timetable.exam_date)
    )
    tt_entries = tt_res.scalars().all()
    active_tt = [
        TimetableResponse(
            id=str(e.id), department=e.department, semester=e.semester,
            subject_name=e.subject_name, exam_date=e.exam_date,
            exam_time=e.exam_time, status=e.status,
            published_at=str(e.published_at) if e.published_at else None,
            created_at=str(e.created_at) if e.created_at else None,
        )
        for e in tt_entries
    ]

    return FacultyOverviewResponse(
        assigned_semesters=sorted(all_semesters),
        assigned_subjects=subjects,
        total_students=len(students),
        subject_stats=subject_stats,
        active_timetable=active_tt,
    )


@router.post("/faculty/marks", response_model=MessageResponse)
async def faculty_upload_marks(
    body: MarksUpload,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(faculty_only),
):
    """Upload internal marks for a student."""
    # Verify student is faculty's subordinate
    student_id = uuid.UUID(body.student_id)
    result = await db.execute(
        select(AuthUser).where(AuthUser.id == student_id, AuthUser.parent_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=403, detail="Student is not under your supervision.")

    mark = InternalMarks(
        student_id=student_id,
        subject_name=body.subject_name,
        semester=body.semester,
        marks_obtained=body.marks_obtained,
        max_marks=body.max_marks,
        uploaded_by=current_user.id,
    )
    db.add(mark)
    await db.flush()

    avg_res = await db.execute(
        select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
        .where(
            InternalMarks.uploaded_by == current_user.id,
            InternalMarks.student_id == student_id,
            InternalMarks.semester == body.semester,
            InternalMarks.subject_name == body.subject_name,
        )
    )
    avg_pct = float(avg_res.scalar() or 0.0)

    if avg_pct >= 85.0:
        category = StudentPerformanceCategoryType.TOP
    elif avg_pct < 50.0:
        category = StudentPerformanceCategoryType.WEAK
    else:
        category = StudentPerformanceCategoryType.AVERAGE

    existing_res = await db.execute(
        select(StudentPerformanceCategory).where(
            StudentPerformanceCategory.computed_by == current_user.id,
            StudentPerformanceCategory.student_id == student_id,
            StudentPerformanceCategory.semester == body.semester,
            StudentPerformanceCategory.subject_name == body.subject_name,
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        existing.average_percentage = avg_pct
        existing.category = category
    else:
        db.add(
            StudentPerformanceCategory(
                student_id=student_id,
                computed_by=current_user.id,
                semester=body.semester,
                subject_name=body.subject_name,
                average_percentage=avg_pct,
                category=category,
            )
        )

    await db.commit()
    return MessageResponse(message="Marks uploaded successfully.")


@router.put("/faculty/marks/{mark_id}", response_model=MessageResponse)
async def faculty_update_marks(
    mark_id: uuid.UUID,
    body: MarksUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(faculty_only),
):
    """Update marks (only if not locked by HOD)."""
    result = await db.execute(
        select(InternalMarks).where(
            InternalMarks.id == mark_id,
            InternalMarks.uploaded_by == current_user.id,
        )
    )
    mark = result.scalar_one_or_none()
    if not mark:
        raise HTTPException(status_code=404, detail="Mark entry not found.")

    if mark.is_locked:
        raise HTTPException(status_code=403, detail="Marks are locked by HOD and cannot be edited.")

    if body.marks_obtained is not None:
        mark.marks_obtained = body.marks_obtained
    if body.max_marks is not None:
        mark.max_marks = body.max_marks

    await db.flush()

    avg_res = await db.execute(
        select(func.avg(InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks))
        .where(
            InternalMarks.uploaded_by == current_user.id,
            InternalMarks.student_id == mark.student_id,
            InternalMarks.semester == mark.semester,
            InternalMarks.subject_name == mark.subject_name,
        )
    )
    avg_pct = float(avg_res.scalar() or 0.0)

    if avg_pct >= 85.0:
        category = StudentPerformanceCategoryType.TOP
    elif avg_pct < 50.0:
        category = StudentPerformanceCategoryType.WEAK
    else:
        category = StudentPerformanceCategoryType.AVERAGE

    existing_res = await db.execute(
        select(StudentPerformanceCategory).where(
            StudentPerformanceCategory.computed_by == current_user.id,
            StudentPerformanceCategory.student_id == mark.student_id,
            StudentPerformanceCategory.semester == mark.semester,
            StudentPerformanceCategory.subject_name == mark.subject_name,
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        existing.average_percentage = avg_pct
        existing.category = category
    else:
        db.add(
            StudentPerformanceCategory(
                student_id=mark.student_id,
                computed_by=current_user.id,
                semester=mark.semester,
                subject_name=mark.subject_name,
                average_percentage=avg_pct,
                category=category,
            )
        )

    await db.commit()
    return MessageResponse(message="Marks updated successfully.")


@router.get("/faculty/marks", response_model=list[MarksResponse])
async def faculty_view_marks(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(faculty_only),
):
    """View marks uploaded by this faculty."""
    result = await db.execute(
        select(InternalMarks, AuthUser.name)
        .join(AuthUser, InternalMarks.student_id == AuthUser.id)
        .where(InternalMarks.uploaded_by == current_user.id)
        .order_by(InternalMarks.semester, InternalMarks.subject_name)
    )
    rows = result.all()
    return [
        MarksResponse(
            id=str(m.id), student_id=str(m.student_id), student_name=name,
            subject_name=m.subject_name, semester=m.semester,
            marks_obtained=m.marks_obtained, max_marks=m.max_marks,
            is_locked=m.is_locked, uploaded_by=str(m.uploaded_by),
        )
        for m, name in rows
    ]


# ══════════════════════════════════════════════════════════════════════════
#  STUDENT DASHBOARD ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════


@router.get("/student/academic", response_model=StudentAcademicResponse)
async def student_academic(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Academic overview: GPA, marks, rank, performance."""
    # Get all marks for this student
    result = await db.execute(
        select(InternalMarks)
        .where(InternalMarks.student_id == current_user.id)
        .order_by(InternalMarks.semester, InternalMarks.subject_name)
    )
    marks = result.scalars().all()

    total = sum(m.marks_obtained for m in marks)
    max_possible = sum(m.max_marks for m in marks)
    percentage = (total / max_possible * 100) if max_possible > 0 else 0.0
    # Simple GPA: percentage / 10, capped at 10
    gpa = min(round(percentage / 10, 2), 10.0)

    marks_detail = [
        StudentMarksDetail(
            subject_name=m.subject_name, semester=m.semester,
            marks_obtained=m.marks_obtained, max_marks=m.max_marks,
            percentage=round(m.marks_obtained / m.max_marks * 100, 2) if m.max_marks > 0 else 0,
        )
        for m in marks
    ]

    # Calculate rank among peers (students with same parent)
    parent_id = current_user.parent_id
    rank = 1
    total_in_class = 1
    if parent_id:
        peers = await get_children(db, parent_id)
        peer_students = [p for p in peers if p.role == "STUDENT"]
        total_in_class = len(peer_students)

        peer_avgs = []
        for p in peer_students:
            r = await db.execute(
                select(
                    func.sum(InternalMarks.marks_obtained),
                    func.sum(InternalMarks.max_marks),
                ).where(InternalMarks.student_id == p.id)
            )
            pm_total, pm_max = r.one()
            peer_pct = ((pm_total or 0) / (pm_max or 1)) * 100
            peer_avgs.append((p.id, peer_pct))

        peer_avgs.sort(key=lambda x: x[1], reverse=True)
        for i, (pid, _) in enumerate(peer_avgs):
            if pid == current_user.id:
                rank = i + 1
                break

    return StudentAcademicResponse(
        gpa=gpa,
        total_marks=total,
        max_possible=max_possible,
        percentage=round(percentage, 2),
        rank=rank,
        total_in_class=total_in_class,
        marks=marks_detail,
    )


@router.get("/student/timetable", response_model=list[TimetableResponse])
async def student_timetable(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Read-only timetable view for student's department. Auto-archives past exams."""
    dept = current_user.department
    if not dept:
        return []

    from datetime import date
    today = date.today().isoformat()
    
    # Auto-archive past exams for this department
    await db.execute(
        update(Timetable)
        .where(Timetable.department == dept, Timetable.status == "active", Timetable.exam_date < today)
        .values(status="archived")
    )
    await db.commit()

    result = await db.execute(
        select(Timetable).where(Timetable.department == dept, Timetable.status == "active").order_by(Timetable.exam_date)
    )
    entries = result.scalars().all()
    return [
        TimetableResponse(
            id=str(e.id), department=e.department, semester=e.semester,
            subject_name=e.subject_name, exam_date=e.exam_date,
            exam_time=e.exam_time, status=e.status,
            published_at=str(e.published_at) if e.published_at else None,
            created_at=str(e.created_at) if e.created_at else None,
        )
        for e in entries
    ]


@router.get("/student/certificates", response_model=list[CertificateResponse])
async def student_certificates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """List certificates for the current student."""
    result = await db.execute(
        select(Certificate).where(Certificate.student_id == current_user.id)
        .order_by(Certificate.uploaded_at.desc())
    )
    certs = result.scalars().all()
    return [
        CertificateResponse(
            id=str(c.id), title=c.title, file_name=c.file_name,
            is_verified=c.is_verified, points=c.points,
            uploaded_at=str(c.uploaded_at) if c.uploaded_at else None,
        )
        for c in certs
    ]


@router.get("/student/projects", response_model=list[ProjectResponse])
async def student_projects(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """List projects for the current student."""
    from app.models.project import Project
    result = await db.execute(
        select(Project).where(Project.student_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [
        ProjectResponse(
            id=str(p.id),
            project_name=p.project_name,
            description=p.description,
            github_url=p.github_url,
            tech_stack=p.tech_stack,
            verification_status=p.verification_status,
            verification_run_id=str(p.verification_run_id) if p.verification_run_id else None,
            created_at=str(p.created_at) if p.created_at else None,
        )
        for p in projects
    ]


@router.post("/student/certificates", response_model=MessageResponse)
async def upload_certificate(
    title: str = Form(""),
    description: str = Form(None),
    file: UploadFile | None = File(None),
    github_url: str | None = Form(None),
    tech_stack: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
    """Upload a certificate file and/or a GitHub project URL."""
    if not file and not github_url:
        raise HTTPException(status_code=400, detail="Must provide either a file or a GitHub URL.")

    # Process certificate file if provided
    if file:
        if not title:
            raise HTTPException(status_code=400, detail="Title is required when uploading a certificate file.")
            
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file.")

        file_hash = sha256_hex(file_bytes)
        file_name, file_path = await save_certificate_file(
            CERT_DIR,
            str(current_user.id),
            file.filename,
            file_bytes,
        )

        cert, block = await create_certificate_and_block(
            db=db,
            student_id=current_user.id,
            title=title,
            description=description,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
        )

        # Trigger Verification Agent
        try:
            from app.agents.verification_agent.controller import VerificationController
            import logging
            logger = logging.getLogger(__name__)

            # Reset file pointer since we already read it
            await file.seek(0)

            controller = VerificationController(db=db)
            verification = await controller.verify(
                user_id=current_user.id,
                file=file,
                link=None,
                profile_data=None,
            )

            # Update certificate based on AI Verification Result
            if verification.status == "verified":
                cert.is_verified = True
                cert.points = 10  # Standard 10 points for a valid certificate
                logger.info("[CERT_UPLOAD] Certificate %s verified successfully: %s", cert.id, verification.confidence_score)
            else:
                cert.is_verified = False
                cert.points = 0
                logger.warning("[CERT_UPLOAD] Certificate %s failed verification: %s", cert.id, verification.status)
            
            db.add(cert)
            await db.commit()

        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("[CERT_UPLOAD] Agent Verification encountered an error: %s", exc)

    # Process GitHub project if provided
    if github_url:
        if not title:
            raise HTTPException(status_code=400, detail="Project name (title) is required when submitting a GitHub URL.")
            
        from app.models.project import Project
        
        new_project = Project(
            student_id=current_user.id,
            project_name=title,
            description=description,
            github_url=github_url,
            tech_stack=tech_stack,
        )
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)

    return MessageResponse(message="Successfully submitted.")


@router.post("/certificates/backfill-points", response_model=MessageResponse)
async def backfill_certificate_points(
    points: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RoleChecker(["CUDAS_ADMIN", "COLLEGE_PRINCIPAL"])),
):
    """Backfill points for certificates that currently have 0 points."""
    if isinstance(current_user, dict):
        return MessageResponse(message="Backfill completed.")

    if points < 0:
        raise HTTPException(status_code=400, detail="Points must be >= 0")

    result = await db.execute(
        update(Certificate)
        .where(Certificate.points == 0)
        .values(points=points)
    )
    updated = result.rowcount or 0
    return MessageResponse(message=f"Backfilled points for {updated} certificates.")


# ── Leaderboard ─────────────────────────────────────────────────────────


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    department: str = None,
    semester: int = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get student leaderboard filterable by department and semester."""
    # We want to show students, their avg marks %, and certificate points.
    # Total Score = avg_marks_pct + cert_points (or some weighted sum)

    marks_q = select(
        InternalMarks.student_id.label("student_id"),
        func.avg(
            InternalMarks.marks_obtained * 100.0 / InternalMarks.max_marks
        ).label("avg_marks"),
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

    query = (
        select(
            AuthUser.id,
            AuthUser.name,
            AuthUser.email,
            AuthUser.department,
            func.coalesce(AuthUser.semester, marks_sq.c.marks_semester).label("semester"),
            func.coalesce(marks_sq.c.avg_marks, 0).label("avg_marks"),
            func.coalesce(cert_sq.c.cert_points, 0).label("cert_points"),
        )
        .outerjoin(marks_sq, AuthUser.id == marks_sq.c.student_id)
        .outerjoin(cert_sq, AuthUser.id == cert_sq.c.student_id)
        .where(AuthUser.role == "STUDENT")
    )

    if department:
        query = query.where(AuthUser.department == department)
    if semester is not None:
        query = query.where(
            or_(
                AuthUser.semester == semester,
                marks_sq.c.marks_semester == semester,
            )
        )

    query = query.order_by(func.coalesce(marks_sq.c.avg_marks, 0).desc())

    res = await db.execute(query)
    rows = res.all()

    def _badge_for_score(total_score: float) -> str | None:
        if total_score >= 90:
            return "gold"
        if total_score >= 75:
            return "silver"
        if total_score >= 50:
            return "bronze"
        return None
    
    leaderboard = []
    for i, r in enumerate(rows):
        avg = float(r.avg_marks or 0)
        pts = int(r.cert_points or 0)
        total = avg + pts # Weighted score
        
        leaderboard.append(LeaderboardEntry(
            rank=i + 1,
            student_id=str(r.id),
            name=r.name,
            email=r.email,
            department=r.department,
            semester=r.semester,
            average_marks=round(avg, 2),
            certificate_points=pts,
            total_score=round(total, 2),
            badge=_badge_for_score(total)
        ))
    
    return leaderboard


# ── Career Roadmap ───────────────────────────────────────────────────────────


@router.post("/student/career-roadmap")
async def generate_career_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a personalized career roadmap based on student's goal, academics, and skills."""
    import logging
    _logger = logging.getLogger(__name__)

    if current_user.role != "STUDENT":
        return {"success": False, "error": "Only students can generate career roadmaps"}
    
    if not current_user.goal:
        return {"success": False, "error": "Please set your career goal first"}
    
    _logger.info("Career roadmap request from user %s, goal='%s'", current_user.id, current_user.goal)
    
    # Get student's academic data
    marks_result = await db.execute(
        select(InternalMarks).where(InternalMarks.student_id == current_user.id)
    )
    marks = marks_result.scalars().all()
    
    total_marks = sum(m.marks_obtained for m in marks)
    total_max = sum(m.max_marks for m in marks)
    avg_percentage = (total_marks / total_max * 100) if total_max > 0 else 0
    
    cert_result = await db.execute(
        select(Certificate).where(Certificate.student_id == current_user.id)
    )
    certificates = cert_result.scalars().all()
    cert_points = sum(c.points for c in certificates)
    
    student_data = {
        "goal": current_user.goal,
        "department": current_user.department or "Not specified",
        "semester": current_user.semester or 0,
        "skills": current_user.skills or [],
        "average_percentage": round(avg_percentage, 2),
        "total_certificates": len(certificates),
        "certificate_points": cert_points,
        "certifications": [{"title": c.title, "points": c.points} for c in certificates],
        "subjects": [{"name": m.subject_name, "percentage": round(m.marks_obtained / m.max_marks * 100, 2)} for m in marks]
    }
    
    _logger.info("Student profile built: %d subjects, %d certs, avg=%.1f%%",
                 len(marks), len(certificates), avg_percentage)

    # ── Ensure academic profile is in RAG knowledge base ─────────────────
    try:
        from app.models.rag import Document
        existing_profile = await db.execute(
            select(Document).where(
                Document.user_id == current_user.id,
                Document.title.like("Academic Profile -%"),
            )
        )
        if existing_profile.scalar_one_or_none() is None:
            # Build academic profile text and index it
            profile_lines = [
                f"Student: {current_user.name}",
                f"Department: {student_data['department']}",
                f"Semester: {student_data['semester']}",
                f"Career Goal: {student_data['goal']}",
                f"Average Academic Performance: {student_data['average_percentage']}%",
                f"Skills: {', '.join(student_data['skills']) if student_data['skills'] else 'None'}",
                f"Total Certificates: {student_data['total_certificates']} ({cert_points} points)",
            ]
            if student_data['certifications']:
                profile_lines.append("Certifications:")
                for cert in student_data['certifications']:
                    profile_lines.append(f"  - {cert['title']} ({cert['points']} pts)")
            if student_data['subjects']:
                profile_lines.append("Subjects:")
                for subj in student_data['subjects'][:10]:
                    profile_lines.append(f"  - {subj['name']}: {subj['percentage']}%")

            profile_text = "\n".join(profile_lines)

            from app.services.chunking_service import ChunkingService
            from app.services.embedding_service import EmbeddingService
            from app.services.vector_store_service import VectorStoreService

            chunker = ChunkingService()
            chunks = chunker.chunk_text(profile_text)
            if chunks:
                embedder = EmbeddingService()
                vectors = embedder.embed_batch(chunks)
                store = VectorStoreService(db)
                await store.store_document_with_embeddings(
                    user_id=current_user.id,
                    title=f"Academic Profile - {current_user.name}",
                    raw_content=profile_text,
                    chunks=chunks,
                    vectors=vectors,
                    content_type="text/plain",
                    agent_type="career_roadmap",
                )
                await db.flush()
                _logger.info("RAG: Auto-indexed academic profile with %d chunks", len(chunks))
    except Exception as e:
        _logger.warning("RAG auto-indexing failed (non-fatal): %s", e)

    # Generate roadmap using the Career Roadmap Agent (LLM-backed)
    try:
        from app.agents.career_roadmap.agent import CareerRoadmapAgent
        agent = CareerRoadmapAgent(db)
        roadmap = await agent.generate_roadmap(
            user_id=current_user.id,
            student_data=student_data,
        )
        _logger.info("Career roadmap generated successfully: '%s' with %d steps",
                     roadmap.get("title", "N/A"), len(roadmap.get("steps", [])))
        return {"success": True, "data": roadmap}
    except Exception as e:
        _logger.error("Career roadmap generation failed: %s", e, exc_info=True)
        # Fallback to old template-based generator
        try:
            from app.services.ai_service import generate_career_roadmap as _old_generate
            roadmap_text = await _old_generate(student_data)
            _logger.info("Fallback roadmap generated (legacy format)")
            return {"success": True, "data": {"roadmap": roadmap_text}}
        except Exception:
            return {"success": False, "error": f"Failed to generate career roadmap: {str(e)}"}


