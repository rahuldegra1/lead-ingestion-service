from pathlib import Path

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'leads.db'}"

# SQLite requires check_same_thread=False for multi-threaded FastAPI handlers
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# 1. SQLAlchemy Table Schema
class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    budget_inr = Column(Integer, nullable=False)
    phone = Column(String, nullable=False)


# 2. Database Schema Initializer
def init_db():
    Base.metadata.create_all(bind=engine)


# 3. Request Session Lifecycle Generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
