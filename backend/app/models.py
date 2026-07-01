"""SQLAlchemy ORM models — pure data containers, no business logic."""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from .database import Base


class ProcessingStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, nullable=True)
    cache_version   = Column(Integer, nullable=False, default=1, server_default="1")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents  = relationship("Document",  back_populates="owner", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog",  back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id                = Column(Integer, primary_key=True, index=True)
    filename          = Column(String, nullable=False, index=True)
    owner_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    file_size         = Column(Integer, default=0)
    file_type         = Column(String, default="")
    num_chunks        = Column(Integer, default=0)
    processing_status = Column(Enum(ProcessingStatus,values_callable=lambda enum_cls: [e.value for e in enum_cls],
        name="processingstatus",), nullable=False,default=ProcessingStatus.PENDING)
    processing_time   = Column(Float, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="documents")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id            = Column(Integer, primary_key=True, index=True)
    owner_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question      = Column(String, nullable=False)
    response_time = Column(Float, nullable=False)
    was_cached    = Column(Integer, nullable=False, default=0, server_default="0")  # 0/1
    created_at    = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="query_logs")
