from app.models.sql_models import User, Resume
from sqlmodel import SQLModel

class ResumeRead(SQLModel):
    id: int
    title: str
    filename: str
    file_url: str
    file_type: str
    file_size: int
    status: str
    upload_date: str
    # Do NOT include the 'user' field here

class UserRead(SQLModel):
    id: int
    email: str
    name: str
    picture_url: str | None
    # Do NOT include 'resumes' or 'cover_letters' here