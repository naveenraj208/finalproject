# db.py
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = create_engine("sqlite:///memory.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class MemoryRow(Base):
    __tablename__ = "memory"
    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, nullable=True)
    text = Column(Text)
    summary = Column(Text, nullable=True)
    parent_id = Column(String, nullable=True)
    pinned = Column(Boolean, default=False)
    importance = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_longterm = Column(Boolean, default=False)
    is_assistant = Column(Boolean, default=False)

class QuarantineRow(Base):
    __tablename__ = "quarantine"
    id = Column(String, primary_key=True, index=True)
    text = Column(Text)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
