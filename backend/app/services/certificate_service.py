import base64
import hashlib
import os
from datetime import datetime, timezone

import aiofiles
import qrcode
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Certificate
from app.models.certificate_block import CertificateBlock


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_block_hash(certificate_hash: str, previous_hash: str | None, timestamp: datetime) -> str:
    ts = timestamp.astimezone(timezone.utc).isoformat()
    payload = f"{certificate_hash}{previous_hash or ''}{ts}".encode("utf-8")
    return sha256_hex(payload)


async def save_certificate_file(cert_dir: str, student_id: str, original_filename: str | None, file_bytes: bytes) -> tuple[str, str]:
    os.makedirs(cert_dir, exist_ok=True)

    ext = os.path.splitext(original_filename or "")[1] or ".pdf"
    unique_name = f"{student_id}_{sha256_hex(file_bytes)[:12]}{ext}"
    file_path = os.path.join(cert_dir, unique_name)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    return unique_name, file_path


async def generate_qr_base64_png(data: str) -> str:
    img = qrcode.make(data)
    from io import BytesIO

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


async def create_certificate_and_block(
    *,
    db: AsyncSession,
    student_id,
    title: str,
    description: str | None = None,
    file_name: str,
    file_path: str,
    file_hash: str,
    points: int = 10,
) -> tuple[Certificate, CertificateBlock]:
    existing = await db.execute(select(Certificate).where(Certificate.file_hash == file_hash))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Certificate already uploaded previously.")

    timestamp = datetime.now(timezone.utc)

    try:
        tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        async with tx_ctx:
            cert = Certificate(
                student_id=student_id,
                title=title,
                description=description,
                file_name=file_name,
                file_path=file_path,
                file_hash=file_hash,
                points=points,
                uploaded_at=timestamp,
            )
            db.add(cert)
            await db.flush()

            last_block_res = await db.execute(
                select(CertificateBlock)
                .order_by(CertificateBlock.block_index.desc())
                .limit(1)
                .with_for_update()
            )
            last_block = last_block_res.scalar_one_or_none()

            previous_hash = last_block.block_hash if last_block else None
            block_index = (last_block.block_index + 1) if last_block else 0
            block_hash = compute_block_hash(file_hash, previous_hash, timestamp)

            block = CertificateBlock(
                certificate_hash=file_hash,
                previous_hash=previous_hash,
                block_hash=block_hash,
                timestamp=timestamp,
                block_index=block_index,
            )
            db.add(block)
            await db.flush()

        return cert, block

    except IntegrityError as e:
        # Handles race condition on unique(file_hash)
        raise HTTPException(status_code=400, detail="Certificate already uploaded previously.") from e


async def verify_chain_integrity(db: AsyncSession) -> bool:
    res = await db.execute(select(CertificateBlock).order_by(CertificateBlock.block_index.asc()))
    blocks = res.scalars().all()
    if not blocks:
        return True

    prev_hash: str | None = None
    expected_index = 0
    for b in blocks:
        if b.block_index != expected_index:
            return False

        if b.previous_hash != prev_hash:
            return False

        expected_hash = compute_block_hash(b.certificate_hash, b.previous_hash, b.timestamp)
        if b.block_hash != expected_hash:
            return False

        prev_hash = b.block_hash
        expected_index += 1

    return True
