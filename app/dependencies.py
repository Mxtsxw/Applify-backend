from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token
from app.core.database import get_session
from app.models.sql_models import User
from sqlmodel import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/google")

def validate_token(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_access_token(token)

def get_current_user(token: dict = Depends(validate_token), db: Session = Depends(get_session)) -> User:
    user_id = token.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user