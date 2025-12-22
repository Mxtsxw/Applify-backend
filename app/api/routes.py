from fastapi import APIRouter
from app.api import auth, analysis, resumes, cover_letters, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(analysis.router, prefix="/analyze", tags=["Analysis"])
api_router.include_router(cover_letters.router, prefix="/cover-letters", tags=["Cover Letters"])

@api_router.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Applify API!"}

@api_router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}