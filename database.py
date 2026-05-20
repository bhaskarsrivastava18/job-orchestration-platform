from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bhaskar:secret@localhost:5432/jobs")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class JobRecord(Base):
    __tablename__ = "jobs"
    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(Text)
    priority    = Column(Integer, default=5)
    status      = Column(String, default="pending")
    created_at  = Column(DateTime, default=datetime.utcnow)
    started_at  = Column(DateTime, nullable=True)
    completed_at= Column(DateTime, nullable=True)
    error       = Column(Text, nullable=True)
def init_db():
    Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()