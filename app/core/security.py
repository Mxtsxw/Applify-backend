import time
import logging
from authlib.jose import jwt, JoseError
from fastapi import HTTPException, status
from app.config import settings

def create_access_token(user_payload: dict) -> str:
    header = {'alg': 'HS256'}
    payload = user_payload.copy()
    # 1 hour expiration
    payload['exp'] = int(time.time()) + 3600 
    return jwt.encode(header, payload, settings.SECRET_KEY).decode('utf-8')

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY)
        payload.validate()
        return payload
    except JoseError as e:
        logging.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )