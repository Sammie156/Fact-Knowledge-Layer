from collections.abc import Generator
from sqlalchemy.orm import Session
from core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it closes after request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
