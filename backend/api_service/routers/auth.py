"""ChainSentry Authentication Router."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.security import verify_password, create_access_token, create_refresh_token, decode_token
from backend.chainsentry_common.schemas import LoginRequest, TokenResponse, UserResponse
from backend.case_svc.models import User
from backend.case_svc.audit import log_action
from backend.api_service.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        log_action(
            db=db,
            action="LOGIN_FAILED",
            actor_name=login_data.username,
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access_token = create_access_token(data={"sub": user.id, "role": user.role, "username": user.username})
    refresh_token = create_refresh_token(data={"sub": user.id})

    log_action(
        db=db,
        action="LOGIN_SUCCESS",
        actor_id=user.id,
        actor_name=user.username,
        ip_address=request.client.host if request.client else None
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/refresh")
def refresh_token(token: str, db: Session = Depends(get_db)):
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    new_access = create_access_token(data={"sub": user.id, "role": user.role, "username": user.username})
    return {"access_token": new_access, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_action(
        db=db,
        action="LOGOUT",
        actor_id=current_user.id,
        actor_name=current_user.username,
        ip_address=request.client.host if request.client else None
    )
    return {"message": "Successfully logged out"}
