from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ✅ Agar online server par environment variable hai toh wo lo, nahi toh local SQLite
# (Jab tum Render par daloge, wahan DATABASE_URL set karenge)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./school.db")

# ✅ PostgreSQL ke liye check (Render 'postgres://' deta hai, SQLAlchemy ko 'postgresql://' chahiye)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ Engine Creation Logic
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite ke liye (Local Computer)
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL ke liye (Online Cloud)
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()