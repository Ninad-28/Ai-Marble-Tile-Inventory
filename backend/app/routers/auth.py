from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.schemas.auth import LoginRequest, TokenResponse, AdminOut
from app.middleware.auth import (
    verify_password, create_access_token, get_current_admin
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == request.email).first()

    if not admin or not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    token = create_access_token(data={"sub": admin.email})

    return TokenResponse(
        access_token=token,
        admin_name=admin.name,
        admin_email=admin.email
    )

@router.get("/me", response_model=AdminOut)
def get_me(current_admin: Admin = Depends(get_current_admin)):
    return current_admin

@router.post("/logout")
def logout(current_admin: Admin = Depends(get_current_admin)):
    # JWT is stateless — client drops the token
    return {"message": f"Goodbye, {current_admin.name}"}