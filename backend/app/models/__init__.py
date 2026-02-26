"""Re-export all ORM models for convenient imports and Alembic discovery."""

from app.models.interview import (  # noqa: F401
    AnswerScore,
    Answer,
    Difficulty,
    InterviewMemory,
    InterviewReport,
    InterviewSession,
    Question,
    QuestionType,
    SessionStatus,
    Skill,
    StudentProfile,
    User,
    UserRole,
)

from app.models.auth import (  # noqa: F401
    AuthUser,
    AuthUserRole,
    College,
    ApprovalStatus,
    Company,
    Timetable,
    InternalMarks,
    Certificate,
    Department,
    MentorAssignment,
)
