import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CertificateBlock(Base):
    __tablename__ = "certificate_blocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    certificate_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("certificates.file_hash", ondelete="CASCADE"),
        nullable=False,
    )

    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_certificate_blocks_certificate_hash", "certificate_hash"),
    )
