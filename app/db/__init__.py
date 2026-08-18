"""Database infrastructure kept separate from domain services."""

from app.db.session import Database

__all__ = ["Database"]
