from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_certificate_pipeline(
    *,
    db: AsyncSession,
    user_id: uuid.UUID | None,
    file: UploadFile | None,
    profile_data: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str]]:
    from app.agents.verification_agent.utils.file_utils import read_upload_file_bytes, sha256_hex
    from app.agents.verification_agent.pipelines.extractors.certificate_extractor import extract_certificate_structured
    from app.agents.verification_agent.validators.format_validator import validate_certificate_format
    from app.agents.verification_agent.validators.metadata_validator import validate_certificate_metadata
    from app.agents.verification_agent.validators.source_validator import validate_certificate_source
    from app.agents.verification_agent.validators.consistency_validator import validate_cross_profile_consistency
    from app.agents.verification_agent.ml_models.placeholder_fraud import fraud_score_placeholder

    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    if file is None:
        issues.append("No file provided for certificate verification")
        return {}, {"format_score": 0, "metadata_score": 0, "source_score": 0, "consistency_score": 0, "ml_score": 0.5}, issues, verified_fields, recommendations

    file_bytes = await read_upload_file_bytes(file)
    file_hash = sha256_hex(file_bytes)

    extracted = await extract_certificate_structured(file=file, file_bytes=file_bytes)
    extracted["file_hash"] = file_hash

    format_res = await validate_certificate_format(extracted)
    metadata_res = await validate_certificate_metadata(extracted)
    source_res = await validate_certificate_source(db=db, extracted=extracted)
    consistency_res = await validate_cross_profile_consistency(extracted=extracted, profile_data=profile_data)
    ml_res = await fraud_score_placeholder(input_type="certificate", extracted=extracted)

<<<<<<< HEAD
=======
    blockchain_verified = False
    try:
        from sqlalchemy import select
        from app.models.certificate_block import CertificateBlock
        from app.services.certificate_service import verify_chain_integrity

        block_res = await db.execute(select(CertificateBlock).where(CertificateBlock.certificate_hash == file_hash))
        block = block_res.scalar_one_or_none()

        if block is not None:
            is_chain_valid = await verify_chain_integrity(db)
            blockchain_verified = is_chain_valid
    except Exception as e:
        logger.warning("Blockchain validation failed to execute: %s", e)

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
    issues.extend(format_res["issues"])
    issues.extend(metadata_res["issues"])
    issues.extend(source_res["issues"])
    issues.extend(consistency_res["issues"])

    verified_fields.extend(format_res["verified_fields"])
    verified_fields.extend(metadata_res["verified_fields"])

    recommendations.extend(source_res.get("recommendations", []))

    scores = {
        "format_score": format_res["score"],
        "metadata_score": metadata_res["score"],
        "source_score": source_res["score"],
        "consistency_score": consistency_res["score"],
        "ml_score": ml_res["score"],
<<<<<<< HEAD
=======
        "blockchain_verified": blockchain_verified,
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
    }

    return extracted, scores, issues, verified_fields, recommendations
