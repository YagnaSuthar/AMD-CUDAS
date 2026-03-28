from __future__ import annotations

from typing import Any


async def fraud_score_placeholder(*, input_type: str, extracted: dict[str, Any]) -> dict[str, Any]:
    return {"score": 0.5, "model": "placeholder"}
