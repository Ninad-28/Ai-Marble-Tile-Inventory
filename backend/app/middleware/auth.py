from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.admin import Admin
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

# --- Password Utilities ---
def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Fallback for environments where bcrypt backend is misconfigured.
        import hashlib
        print(f"Warning: bcrypt hash fallback: {e}")
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    import hashlib
    
    # If hashed is a SHA256 hex (65 chars hex string), use SHA256 comparison
    if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed):
        return hashlib.sha256(plain.encode()).hexdigest() == hashed
    
    # Otherwise try bcrypt
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# --- JWT Utilities ---
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# --- Route Dependency ---
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    admin = db.query(Admin).filter(
        Admin.email == payload.get("sub"),
        Admin.is_active == True
    ).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or deactivated"
        )

    return admin