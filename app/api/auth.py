from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import select, Session
from authlib.integrations.starlette_client import OAuth
from datetime import datetime
from app.core.database import get_session
from app.core.security import create_access_token
from app.models.sql_models import User
from app.config import settings
from app.core.logging import traffic_logger

router = APIRouter()
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_AUTH_CLIENT_ID,
    client_secret=settings.GOOGLE_AUTH_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get("/google")
async def login(request: Request):
    return await oauth.google.authorize_redirect(request, "http://localhost:8000/api/v1/auth/google/callback")

@router.get("/google/callback")
async def auth_callback(request: Request, db: Session = Depends(get_session)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    
    email = user_info.get("email")
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    
    if not user:
        user = User(email=email, name=user_info.get("name"), picture_url=user_info.get("picture"), provider="google")
        db.add(user)
    else:
        user.last_login = datetime.utcnow()
        if user_info.get("name"):
            user.name = user_info.get("name")
        if user_info.get("picture"):
            user.picture_url = user_info.get("picture")
        db.add(user)
        
    db.commit()
    db.refresh(user)

    traffic_logger.info(f"USER LOGIN SUCCESS: {user.email} (ID: {user.id})")

    frontend_token = create_access_token({
        "sub": str(user.id), 
        "email": user.email,
        "name": user.name,
        "picture": user.picture_url
    })
    return RedirectResponse(url=f"{settings.FRONTEND_AUTH_CALLBACK_URL}?token={frontend_token}")