from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


InputType = Literal["certificate", "project", "profile"]
VerificationStatus = Literal["verified", "suspicious", "failed"]


class VerificationRequest(BaseModel):
    link: Optional[str] = None
    profile_data: Optional[dict[str, Any]] = None


class VerificationExplanation(BaseModel):
    summary: str
    risk_level: Literal["low", "medium", "high"]
    reasons: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class VerificationResponse(BaseModel):
    status: VerificationStatus
    confidence_score: float
    verified_fields: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    trust_score: int
    recommendations: list[str] = Field(default_factory=list)
    explanation: dict[str, Any] = Field(default_factory=dict)
<<<<<<< HEAD
=======
    contribution_summary: Optional[dict[str, Any]] = Field(default=None, description="Deep GitHub contribution analysis")
    blockchain_verified: Optional[bool] = Field(default=None, description="Blockchain verification status for certs")
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

    input_type: InputType
    run_id: str


class VerificationFeedbackRequest(BaseModel):
    is_correct: bool
    notes: Optional[str] = None
