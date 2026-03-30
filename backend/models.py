from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class Job(BaseModel):
    id: str
    url: str
    status: JobStatus
    title: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SubmitRequest(BaseModel):
    url: str
