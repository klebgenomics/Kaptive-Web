from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./kaptive_jobs.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    
    jobs = relationship("Job", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="Pending")
    species = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    finish_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Store the extracted Kaptive metrics right in the row!
    results = Column(JSON, nullable=True)
    
    user = relationship("User", back_populates="jobs")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)