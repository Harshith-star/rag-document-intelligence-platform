from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Any


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    num_chunks: int
    processing_status: str
    processing_time: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    limit: int


class DocumentRename(BaseModel):
    filename: str = Field(min_length=1)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]
    cached: bool = False


class DashboardStats(BaseModel):
    total_documents: int
    storage_used_bytes: int
    questions_asked: int
    cache_hits: int
    avg_response_time_seconds: float
    recent_questions: list[Any] = []
