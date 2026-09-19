"""
Seed the database with a large, consistent demo dataset.

Creates colleges (principal -> HODs -> faculty mentors -> students), companies
(company admin -> recruiters -> jobs -> applications -> interview pipelines),
plus marks, timetables, skills, projects, certificates, messages and
notifications.

All demo accounts use the domain @cudasdemo.com and the same password.

Usage (from the backend folder):
    python seed_demo_data.py            # seed (skips if demo data exists)
    python seed_demo_data.py --reset    # delete demo data, then seed again
"""

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import delete, insert, select, text

from app.core.database import engine, async_session_factory
from app.core.security import hash_password
from app.models.auth import (
    ApprovalStatus, AuthUser, AuthUserRole, Certificate, College, Company, Department,
    InternalMarks, MentorAssignment, StudentPerformanceCategory, StudentPerformanceCategoryType,
    SubjectAssignment, Timetable,
)
from app.models.interview import Skill, StudentProfile
from app.models.job import Job
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.message import Message, MessageType, Notification, NotificationType
from app.models.pipeline import InterviewPipeline, PipelineStatus
from app.models.project import Project

DOMAIN = "cudasdemo.com"
PASSWORD = "Cudas@123"
random.seed(42)
NOW = datetime.now(timezone.utc)

# ── Reference data ────────────────────────────────────────────────────────

FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Shaurya",
         "Ananya", "Diya", "Aadhya", "Saanvi", "Pari", "Myra", "Anika", "Navya", "Kiara", "Riya",
         "Rohan", "Karan", "Dev", "Yash", "Harsh", "Meera", "Priya", "Sneha", "Pooja", "Kavya",
         "Nikhil", "Rahul", "Aman", "Tanvi", "Isha", "Neha", "Kunal", "Parth", "Dhruv", "Jiya"]
LAST = ["Patel", "Shah", "Sharma", "Mehta", "Desai", "Joshi", "Iyer", "Reddy", "Nair", "Gupta",
        "Verma", "Singh", "Kapoor", "Chauhan", "Trivedi", "Pandya", "Rao", "Kulkarni", "Bhatt", "Malhotra"]

COLLEGES = [
    ("Gujarat Institute of Technology", "git"),
    ("Western India Engineering College", "wiec"),
    ("Sardar Vallabh Tech University", "svtu"),
]

DEPARTMENTS = {
    "Computer Engineering": ["Data Structures", "Operating Systems", "Database Systems", "Computer Networks", "Machine Learning"],
    "Information Technology": ["Web Technologies", "Software Engineering", "Cloud Computing", "Cyber Security", "Python Programming"],
    "Electronics & Communication": ["Digital Electronics", "Signals & Systems", "Microprocessors", "VLSI Design", "Embedded Systems"],
    "Mechanical Engineering": ["Thermodynamics", "Fluid Mechanics", "Machine Design", "Manufacturing Processes", "CAD/CAM"],
}
DEPT_CODE = {"Computer Engineering": "ce", "Information Technology": "it",
             "Electronics & Communication": "ec", "Mechanical Engineering": "me"}
MENTOR_SEMESTERS = [2, 4, 6, 8]
STUDENTS_PER_MENTOR = 10

SKILLS = {
    "Computer Engineering": ["Python", "Java", "C++", "SQL", "React", "Node.js", "Machine Learning", "DSA", "Git", "Docker"],
    "Information Technology": ["JavaScript", "React", "HTML/CSS", "Python", "AWS", "Linux", "SQL", "Django", "Git", "Figma"],
    "Electronics & Communication": ["C", "Embedded C", "MATLAB", "Verilog", "Arduino", "IoT", "PCB Design", "Python", "Signal Processing", "Raspberry Pi"],
    "Mechanical Engineering": ["AutoCAD", "SolidWorks", "ANSYS", "CATIA", "MATLAB", "3D Printing", "Lean Manufacturing", "Python", "Six Sigma", "Excel"],
}
SOFT = ["Communication", "Teamwork", "Problem Solving", "Leadership", "Time Management"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]

PROJECT_IDEAS = [
    ("Smart Attendance System", "Face-recognition based attendance with a web dashboard.", "Python, OpenCV, Flask"),
    ("E-Commerce Platform", "Full-stack store with cart, payments and admin panel.", "React, Node.js, MongoDB"),
    ("Campus Placement Portal", "Portal connecting students and recruiters with job tracking.", "React, FastAPI, PostgreSQL"),
    ("IoT Weather Station", "Sensor-based weather monitoring with live charts.", "Arduino, MQTT, Grafana"),
    ("Chatbot for College FAQs", "NLP chatbot answering admission and exam queries.", "Python, LangChain, Groq"),
    ("Expense Tracker App", "Mobile-friendly expense tracker with monthly insights.", "React Native, Firebase"),
    ("Traffic Sign Classifier", "CNN model classifying Indian traffic signs.", "TensorFlow, Keras"),
    ("Hostel Management System", "Room allocation, complaints and fee management.", "Django, MySQL"),
    ("Solar Tracker Prototype", "Dual-axis solar tracker improving panel efficiency.", "Embedded C, Servo, LDR"),
    ("Stock Price Predictor", "LSTM-based stock trend prediction with a dashboard.", "Python, PyTorch, Streamlit"),
]
CERTS = ["AWS Cloud Practitioner", "Google Data Analytics", "NPTEL Python for Data Science", "Coursera Machine Learning",
         "Cisco CCNA Basics", "Microsoft Azure Fundamentals", "Oracle Java SE", "Hackathon Winner - SIH Internal",
         "IBM Full Stack Developer", "Udemy React Complete Guide", "NPTEL IoT", "Meta Front-End Developer"]

COMPANIES = [
    ("TechNova Solutions", "technova"), ("InfyEdge Systems", "infyedge"), ("CloudMatrix Labs", "cloudmatrix"),
    ("DataPulse Analytics", "datapulse"), ("ByteForge Technologies", "byteforge"),
    ("NextGen Robotics", "nextgen"), ("GreenGrid Energy", "greengrid"), ("FinCore Fintech", "fincore"),
]
JOB_TITLES = [
    ("Software Engineer Intern", "Work with the core product team on backend APIs and features.", "3.5", "Ahmedabad"),
    ("Frontend Developer", "Build responsive React interfaces and reusable UI components.", "6", "Bengaluru"),
    ("Data Analyst Trainee", "Analyse business data and build dashboards for stakeholders.", "4.5", "Pune"),
    ("Machine Learning Engineer", "Train and deploy ML models for production use cases.", "10", "Hyderabad"),
    ("Cloud Support Associate", "Support customers on cloud infrastructure and deployments.", "5", "Gandhinagar"),
    ("Embedded Systems Engineer", "Develop firmware for IoT and embedded devices.", "5.5", "Vadodara"),
    ("Graduate Engineer Trainee - Mechanical", "Rotational program across design and manufacturing.", "4", "Surat"),
    ("Full Stack Developer", "Own features end to end across React and Node.js.", "8", "Remote"),
    ("QA Automation Intern", "Write automated tests and improve CI pipelines.", "3", "Ahmedabad"),
    ("Business Technology Analyst", "Bridge business needs and technical solutions.", "7", "Mumbai"),
]


def uid() -> uuid.UUID:
    return uuid.uuid4()


def ago(days: int) -> datetime:
    return NOW - timedelta(days=days, hours=random.randint(0, 23), minutes=random.randint(0, 59))


def name_pool():
    names = [f"{f} {l}" for f in FIRST for l in LAST]
    random.shuffle(names)
    return iter(names)


def slug(full_name: str) -> str:
    first, last = full_name.lower().split(" ", 1)
    return f"{first}.{last.replace(' ', '')}"


async def reset(session) -> None:
    ids = select(AuthUser.id).where(AuthUser.email.like(f"%@{DOMAIN}"))
    # Children first where FKs don't cascade from auth_users directly
    await session.execute(delete(Skill).where(Skill.student_id.in_(ids)))
    await session.execute(delete(AuthUser).where(AuthUser.email.like(f"%@{DOMAIN}")))
    await session.commit()
    print("Removed existing demo data.")


async def seed() -> dict:
    pw = hash_password(PASSWORD)
    names = name_pool()
    rows = {k: [] for k in [
        "users", "colleges", "companies", "departments", "mentors", "subject_assign", "timetables",
        "marks", "perf", "profiles", "skills", "projects", "certs", "jobs", "apps", "pipelines",
        "messages", "notifs"]}
    creds = {}
    enrollment_counter = 1000

    def user(role, name, email, parent=None, **extra):
        u = dict(id=uid(), name=name, email=email, hashed_password=pw, must_reset_password=False,
                 role=role, parent_id=parent, is_verified=True, created_at=ago(random.randint(60, 200)),
                 updated_at=NOW, **extra)
        rows["users"].append(u)
        return u

    students_all = []

    # ── Colleges ─────────────────────────────────────────────────────────
    for ci, (college_name, code) in enumerate(COLLEGES, start=1):
        principal = user(AuthUserRole.COLLEGE_PRINCIPAL, f"Dr. {next(names)}", f"principal.{code}@{DOMAIN}",
                         phone_number=f"+91 98{random.randint(10000000, 99999999)}")
        rows["colleges"].append(dict(id=uid(), name=college_name, principal_id=principal["id"],
                                     status=ApprovalStatus.APPROVED, created_at=principal["created_at"]))
        creds.setdefault("principal", principal["email"])

        for dept, subjects in DEPARTMENTS.items():
            dc = DEPT_CODE[dept]
            rows["departments"].append(dict(id=uid(), name=dept, college_principal_id=principal["id"], created_at=ago(150)))
            hod = user(AuthUserRole.HOD, f"Prof. {next(names)}", f"hod.{dc}.{code}@{DOMAIN}",
                       parent=principal["id"], department=dept)
            creds.setdefault("hod", hod["email"])

            for sem in range(1, 9):
                for si, subj in enumerate(subjects[:3]):
                    exam_day = date.today() + timedelta(days=random.randint(5, 60) if sem % 2 == 0 else -random.randint(10, 90))
                    rows["timetables"].append(dict(
                        id=uid(), department=dept, semester=sem, subject_name=subj,
                        exam_date=exam_day.isoformat(), exam_time=random.choice(["10:00 AM", "02:00 PM"]),
                        created_by=hod["id"], status="active" if exam_day >= date.today() else "archived",
                        published_at=ago(20), created_at=ago(25)))

            for sem in MENTOR_SEMESTERS:
                fac = user(AuthUserRole.FACULTY, f"Prof. {next(names)}", f"faculty.{dc}.s{sem}.{code}@{DOMAIN}",
                           parent=hod["id"], department=dept)
                creds.setdefault("faculty", fac["email"])
                rows["mentors"].append(dict(id=uid(), faculty_id=fac["id"], semester=sem, department=dept,
                                            assigned_by=hod["id"], created_at=ago(90)))
                for k, subj in enumerate(subjects):
                    if k % 2 == MENTOR_SEMESTERS.index(sem) % 2:
                        rows["subject_assign"].append(dict(
                            id=uid(), faculty_id=fac["id"], semester=sem, subject_name=subj,
                            subject_code=f"{dc.upper()}{sem}0{k + 1}", department=dept,
                            assigned_by=hod["id"], created_at=ago(90)))

                for _ in range(STUDENTS_PER_MENTOR):
                    nm = next(names)
                    enrollment_counter += 1
                    skill_names = random.sample(SKILLS[dept], k=random.randint(3, 6))
                    projects = random.sample(PROJECT_IDEAS, k=random.randint(1, 3))
                    stu = user(
                        AuthUserRole.STUDENT, nm, f"{slug(nm)}.{enrollment_counter}@{DOMAIN}", parent=fac["id"],
                        department=dept, semester=sem, enrollment_number=f"{code.upper()}{2026 - sem // 2}{dc.upper()}{enrollment_counter}",
                        phone_number=f"+91 9{random.randint(100000000, 999999999)}",
                        skills=skill_names, github_username=slug(nm).replace(".", "-"),
                        goal=random.choice(["Software Engineer at a product company", "Data Scientist", "Higher studies (MS)",
                                            "Startup founder", "Core engineering role", "Cloud Engineer"]),
                        projects=[{"name": p[0], "description": p[1], "tech_stack": p[2]} for p in projects],
                        project_summary=", ".join(p[0] for p in projects),
                    )
                    stu["_college"] = college_name
                    stu["_dept"] = dept
                    students_all.append(stu)
                    creds.setdefault("student", stu["email"])

                    rows["profiles"].append(dict(student_id=stu["id"], experience_years=0, has_projects=True,
                                                 project_summary=stu["project_summary"],
                                                 resume_text=f"{nm} — {dept} student. Skills: {', '.join(skill_names)}."))
                    for s in skill_names + random.sample(SOFT, 2):
                        rows["skills"].append(dict(id=uid(), student_id=stu["id"], skill_name=s, skill_level=random.choice(LEVELS)))
                    for p in projects:
                        rows["projects"].append(dict(
                            id=uid(), student_id=stu["id"], project_name=p[0], description=p[1],
                            github_url=f"https://github.com/{stu['github_username']}/{p[0].lower().replace(' ', '-')}",
                            tech_stack=p[2], verification_status=random.choice(["pending", "verified", "verified"]),
                            created_at=ago(random.randint(10, 120)), updated_at=NOW))
                    for c in random.sample(CERTS, k=random.randint(0, 3)):
                        rows["certs"].append(dict(
                            id=uid(), student_id=stu["id"], title=c, description=f"Certificate: {c}",
                            file_name=f"{uid().hex}.pdf", file_path=None, file_hash=uid().hex,
                            is_verified=random.random() < 0.7, points=random.choice([10, 20, 30, 50]),
                            uploaded_at=ago(random.randint(5, 100))))

                    # Marks for every completed semester
                    ability = random.gauss(68, 14)
                    for past_sem in range(1, sem + 1):
                        for subj in subjects:
                            score = max(8, min(50, round(random.gauss(ability, 10) / 2)))
                            rows["marks"].append(dict(
                                id=uid(), student_id=stu["id"], subject_name=subj, semester=past_sem,
                                marks_obtained=float(score), max_marks=50.0, uploaded_by=fac["id"],
                                is_locked=past_sem < sem, created_at=ago(30 * (sem - past_sem) + 5)))
                            if past_sem == sem:
                                pct = score * 2
                                cat = (StudentPerformanceCategoryType.TOP if pct >= 80 else
                                       StudentPerformanceCategoryType.AVERAGE if pct >= 55 else
                                       StudentPerformanceCategoryType.WEAK if pct >= 35 else
                                       StudentPerformanceCategoryType.DROPOUT_RISK)
                                rows["perf"].append(dict(
                                    id=uid(), student_id=stu["id"], computed_by=fac["id"], semester=sem,
                                    subject_name=subj, average_percentage=float(pct), category=cat, computed_at=ago(3)))

                    rows["messages"].append(dict(
                        id=uid(), sender_id=fac["id"], recipient_id=stu["id"], message_type=MessageType.COLLEGE_TO_STUDENT,
                        sender_role="FACULTY", receiver_role="STUDENT", receiver_ids=[str(stu["id"])], semester_id=sem,
                        cc_ids=[], subject="Mid-semester mentoring session",
                        body="Please meet me this Friday to review your progress and internship plans.",
                        is_read=random.random() < 0.5, created_at=ago(random.randint(1, 20))))

                rows["messages"].append(dict(
                    id=uid(), sender_id=hod["id"], recipient_id=fac["id"], message_type=MessageType.COLLEGE_TO_FACULTY,
                    sender_role="HOD", receiver_role="FACULTY", receiver_ids=[str(fac["id"])], semester_id=sem,
                    cc_ids=[], subject="Internal marks submission deadline",
                    body="Kindly upload internal marks for your mentees before the end of this week.",
                    is_read=random.random() < 0.6, created_at=ago(random.randint(1, 15))))

            rows["messages"].append(dict(
                id=uid(), sender_id=principal["id"], recipient_id=hod["id"], message_type=MessageType.COLLEGE_TO_HOD,
                sender_role="COLLEGE_PRINCIPAL", receiver_role="HOD", receiver_ids=[str(hod["id"])], semester_id=None,
                cc_ids=[], subject="Placement drive preparation",
                body="Please share the placement readiness report for your department by Monday.",
                is_read=random.random() < 0.5, created_at=ago(random.randint(1, 10))))

    # ── Companies ────────────────────────────────────────────────────────
    recruiters = []
    for company_name, code in COMPANIES:
        admin = user(AuthUserRole.COMPANY_ADMIN, next(names), f"admin.{code}@{DOMAIN}",
                     company_name=company_name, phone_number=f"+91 99{random.randint(10000000, 99999999)}")
        company = dict(id=uid(), name=company_name, company_admin_id=admin["id"],
                       status=ApprovalStatus.APPROVED, created_at=admin["created_at"])
        rows["companies"].append(company)
        creds.setdefault("company_admin", admin["email"])
        for r in range(1, 4):
            rec = user(AuthUserRole.RECRUITER, next(names), f"recruiter{r}.{code}@{DOMAIN}",
                       parent=admin["id"], company_name=company_name)
            creds.setdefault("recruiter", rec["email"])
            recruiters.append((rec, company))
            for title, desc, lpa, loc in random.sample(JOB_TITLES, k=random.randint(2, 3)):
                rows["jobs"].append(dict(
                    id=uid(), company_id=company["id"], recruiter_id=rec["id"], title=title,
                    package_lpa=lpa, bond=random.choice(["None", "1 year", "2 years"]), location=loc,
                    description=f"{desc} Company: {company_name}.", status="ACTIVE",
                    created_at=ago(random.randint(1, 45)), _company_name=company_name))

    # ── Applications & pipelines ─────────────────────────────────────────
    status_weights = [
        (ApplicationStatus.PENDING, 40), (ApplicationStatus.AI_ASSIGNED, 20), (ApplicationStatus.AI_COMPLETED, 15),
        (ApplicationStatus.ROUND2_INVITED, 10), (ApplicationStatus.HIRED, 5), (ApplicationStatus.REJECTED, 10)]
    statuses, weights = zip(*status_weights)
    final_years = [s for s in students_all if s["semester"] >= 6]
    for stu in final_years:
        for job in random.sample(rows["jobs"], k=random.randint(2, 5)):
            st = random.choices(statuses, weights)[0]
            created = ago(random.randint(1, 30))
            rows["apps"].append(dict(
                id=uid(), job_id=job["id"], student_id=stu["id"], status=st,
                ai_score=random.randint(45, 95) if st not in (ApplicationStatus.PENDING, ApplicationStatus.AI_ASSIGNED) else None,
                cover_letter=f"I am excited to apply for {job['title']} and bring my skills in {', '.join(stu['skills'][:3])}.",
                created_at=created, updated_at=NOW))
            pipe_status = {
                ApplicationStatus.AI_ASSIGNED: PipelineStatus.AI_ASSIGNED,
                ApplicationStatus.AI_COMPLETED: PipelineStatus.AI_COMPLETED,
                ApplicationStatus.ROUND2_INVITED: PipelineStatus.ROUND2_INVITED,
                ApplicationStatus.HIRED: PipelineStatus.HIRED,
            }.get(st)
            if pipe_status:
                rows["pipelines"].append(dict(
                    id=uid(), job_id=job["id"], company_id=job["company_id"], recruiter_id=job["recruiter_id"],
                    student_id=stu["id"], ai_session_id=None, status=pipe_status, created_at=created, updated_at=NOW,
                    round2_link="https://meet.google.com/demo-cudas-round" if pipe_status in (PipelineStatus.ROUND2_INVITED, PipelineStatus.HIRED) else None,
                    round2_scheduled_at=NOW + timedelta(days=random.randint(1, 10)) if pipe_status == PipelineStatus.ROUND2_INVITED else None,
                    hired_company_name=job["_company_name"] if pipe_status == PipelineStatus.HIRED else None))
                notif = {
                    PipelineStatus.AI_ASSIGNED: (NotificationType.AI_ASSIGNED, "AI interview assigned", f"Complete your AI interview for {job['title']}."),
                    PipelineStatus.ROUND2_INVITED: (NotificationType.ROUND2_INVITED, "Round 2 invitation", f"You're invited to Round 2 for {job['title']}."),
                    PipelineStatus.HIRED: (NotificationType.HIRED, "Congratulations! You're hired", f"{job['_company_name']} has selected you for {job['title']}."),
                }.get(pipe_status)
                if notif:
                    rows["notifs"].append(dict(
                        id=uid(), user_id=stu["id"], notification_type=notif[0], title=notif[1], message=notif[2],
                        is_read=random.random() < 0.4, is_starred=random.random() < 0.1, sender_role="RECRUITER",
                        meta_json={"job_id": str(job["id"])}, created_at=created + timedelta(hours=2)))

    for rec, company in recruiters:
        for stu in random.sample(final_years, k=4):
            rows["messages"].append(dict(
                id=uid(), sender_id=rec["id"], recipient_id=stu["id"], message_type=MessageType.RECRUITER_TO_STUDENT,
                sender_role="RECRUITER", receiver_role="STUDENT", receiver_ids=[str(stu["id"])], semester_id=None,
                cc_ids=[], subject=f"Opportunity at {company['name']}",
                body="We liked your profile. Please apply to our open roles on CUDAS.",
                is_read=random.random() < 0.5, created_at=ago(random.randint(1, 20))))
    for m in rows["messages"]:
        rows["notifs"].append(dict(
            id=uid(), user_id=m["recipient_id"], notification_type=NotificationType.MESSAGE if m["message_type"] == MessageType.RECRUITER_TO_STUDENT else NotificationType.COLLEGE_MESSAGE,
            title=m["subject"], message=m["body"], is_read=m["is_read"], is_starred=False, sender_role=m["sender_role"],
            meta_json={"message_id": str(m["id"])}, created_at=m["created_at"]))

    # ── Write ────────────────────────────────────────────────────────────
    strip = lambda rs: [{k: v for k, v in r.items() if not k.startswith("_")} for r in rs]
    order = [(AuthUser, "users"), (College, "colleges"), (Company, "companies"), (Department, "departments"),
             (MentorAssignment, "mentors"), (SubjectAssignment, "subject_assign"), (Timetable, "timetables"),
             (InternalMarks, "marks"), (StudentPerformanceCategory, "perf"), (StudentProfile, "profiles"),
             (Skill, "skills"), (Project, "projects"), (Certificate, "certs"), (Job, "jobs"),
             (JobApplication, "apps"), (InterviewPipeline, "pipelines"), (Message, "messages"), (Notification, "notifs")]
    async with async_session_factory() as session:
        for model, key in order:
            data = strip(rows[key])
            for i in range(0, len(data), 1000):
                await session.execute(insert(model), data[i:i + 1000])
        await session.commit()

    return {"counts": {k: len(v) for k, v in rows.items()}, "creds": creds}


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    async with async_session_factory() as session:
        exists = (await session.execute(select(AuthUser.id).where(AuthUser.email.like(f"%@{DOMAIN}")).limit(1))).first()
        if exists:
            if "--reset" not in sys.argv:
                print("Demo data already exists. Run with --reset to recreate it.")
                return
            await reset(session)

    result = await seed()
    print("\nInserted rows:")
    for k, v in result["counts"].items():
        print(f"  {k:<16} {v}")
    print(f"\nPassword for every demo account: {PASSWORD}")
    for role, email in result["creds"].items():
        print(f"  {role:<14} {email}")


if __name__ == "__main__":
    asyncio.run(main())
