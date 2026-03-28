from __future__ import annotations

import hashlib

from fastapi import UploadFile


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def read_upload_file_bytes(file: UploadFile) -> bytes:
    await file.seek(0)
    b = await file.read()
    await file.seek(0)
    return b
