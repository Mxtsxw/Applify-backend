from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Column, Text, Relationship

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True) 
    name: str
    picture_url: Optional[str] = None
    provider: str 
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)

    phone: Optional[str] = None
    location: Optional[str] = None
    
    # Professional Info
    title: Optional[str] = None
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    experience: Optional[str] = None
    education: Optional[str] = None
    
    skills: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Social Links
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

    # Relationship to Resumes
    resumes: List["Resume"] = Relationship(back_populates="user")
    cover_letters: List["CoverLetter"] = Relationship(back_populates="user")

class Resume(SQLModel, table=True):
    __tablename__ = "resumes"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    title: str
    filename: str
    file_url: str
    file_type: str
    file_size: int
    
    status: str = Field(default="active") # "active" or "inactive"
    upload_date: datetime = Field(default_factory=datetime.utcnow)

    # Relationship back to User
    user: Optional["User"] = Relationship(back_populates="resumes")

class CoverLetter(SQLModel, table=True):
    __tablename__ = "cover_letters"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    title: str 
    content: Optional[str] = Field(default=None, sa_column=Column(Text)) # For manual text
    
    # File fields (Optional, only for uploads)
    filename: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    
    method: str = Field(default="manual") # 'upload', 'manual', 'ai_generated'
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="cover_letters")