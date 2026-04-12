"""
Database base module.
Re-exports get_db function from core.database for backward compatibility.
"""

from app.core.database import get_db

__all__ = ["get_db"]
