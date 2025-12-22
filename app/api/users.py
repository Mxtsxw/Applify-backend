from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.dependencies import validate_token, get_session, get_current_user
from app.models.sql_models import User
from app.models.dto import UserRead
from app.models.schemas import UserProfileUpdate

router = APIRouter()

@router.get("/me", response_model=User)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the currently logged-in user. 
    The 'current_user' dependency handles the DB lookup and validation.
    """
    return current_user

@router.put("/me", response_model=User)
def update_my_profile(
    profile_data: UserProfileUpdate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Updates the logged-in user's profile information.
    """
    # Map 'full_name' from schema to 'name' in DB model if present
    if profile_data.full_name:
        current_user.name = profile_data.full_name
        
    # Update other fields dynamically
    update_data = profile_data.model_dump(exclude_unset=True, exclude={"full_name"})
    
    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user