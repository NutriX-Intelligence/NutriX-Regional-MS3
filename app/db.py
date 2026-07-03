import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path

logger = logging.getLogger("db")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "output" / "nutrition_master.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Support PostgreSQL from environment with SQLite fallback
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/nutrix"

engine = None

try:
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info(f"Connecting to PostgreSQL database...")
        # Verify the database connection synchronously
        temp_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with temp_engine.connect() as conn:
            pass
        engine = temp_engine
        logger.info("Successfully connected to PostgreSQL!")
    else:
        raise ValueError("SQLite fallback requested.")
except Exception as e:
    logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite database: {DB_PATH}")
    DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
