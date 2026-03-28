import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import RoleChecker
from app.models.auth import Certificate
from app.models.certificate_block import CertificateBlock
from app.services.certificate_service import (
    create_certificate_and_block,
    generate_qr_base64_png,
    save_certificate_file,
    sha256_hex,
    verify_chain_integrity,
)


router = APIRouter(prefix="/api/certificates", tags=["Certificates"])

student_only = RoleChecker(["STUDENT"])

CERT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "certificate",
)


@router.post("/upload")
async def upload_certificate_blockchain(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(student_only),
):
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

    # ── RAG: Index certificate for knowledge base ─────────────────────────
    rag_msg = ""
    try:
        import logging
        _logger = logging.getLogger(__name__)

        cert_text = f"Certificate: {title}\n"
        if description:
            cert_text += f"Description: {description}\n"
        cert_text += f"Uploaded by student ID: {current_user.id}\n"
        cert_text += f"Student name: {current_user.name}\n"
        if hasattr(current_user, 'department') and current_user.department:
            cert_text += f"Department: {current_user.department}\n"

        if len(cert_text.strip()) > 20:
            from app.services.chunking_service import ChunkingService
            from app.services.embedding_service import EmbeddingService
            from app.services.vector_store_service import VectorStoreService

            chunker = ChunkingService()
            chunks = chunker.chunk_text(cert_text)
            if chunks:
                embedder = EmbeddingService()
                vectors = embedder.embed_batch(chunks)
                store = VectorStoreService(db)
                await store.store_document_with_embeddings(
                    user_id=current_user.id,
                    title=f"Certificate - {title}",
                    raw_content=cert_text,
                    chunks=chunks,
                    vectors=vectors,
                    content_type="text/plain",
                    agent_type="career_roadmap",
                )
                _logger.info("RAG: Indexed certificate '%s' with %d chunks for user %s", title, len(chunks), current_user.id)
                rag_msg = f" RAG: {len(chunks)} chunks indexed."
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("RAG indexing for certificate failed (non-fatal): %s", e)

    verification_url = str(request.base_url).rstrip("/") + f"/api/certificates/verify/{file_hash}"
    qr_base64_png = await generate_qr_base64_png(verification_url)

    return {
        "message": "Certificate uploaded successfully.",
        "certificate_hash": file_hash,
        "block_hash": block.block_hash,
        "block_index": block.block_index,
        "verification_url": verification_url,
        "qr_base64_png": qr_base64_png,
    }


@router.get("/verify/{certificate_hash}")
async def verify_certificate_public(
    certificate_hash: str,
    db: AsyncSession = Depends(get_db),
):
    cert_res = await db.execute(select(Certificate).where(Certificate.file_hash == certificate_hash))
    cert = cert_res.scalar_one_or_none()
    if cert is None:
        return {
            "exists": False,
            "integrity": await verify_chain_integrity(db),
        }

    block_res = await db.execute(
        select(CertificateBlock)
        .where(CertificateBlock.certificate_hash == certificate_hash)
        .order_by(CertificateBlock.block_index.desc())
        .limit(1)
    )
    block = block_res.scalar_one_or_none()

    return {
        "exists": True,
        "uploaded_at": cert.uploaded_at,
        "block_index": block.block_index if block else None,
        "block_hash": block.block_hash if block else None,
        "previous_hash": block.previous_hash if block else None,
        "integrity": await verify_chain_integrity(db),
    }
