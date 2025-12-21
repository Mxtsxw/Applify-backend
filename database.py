from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, Column, Text
from dotenv import load_dotenv
import os

load_dotenv()

# --- 1. The User Model ---
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

# --- 2. The Connection ---
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    """Creates the 'user' table in Postgres if it doesn't exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency for FastAPI endpoints."""
    with Session(engine) as session:
        yield session