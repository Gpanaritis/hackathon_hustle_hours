from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_extensions():
    """Enable required PostgreSQL extensions"""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
