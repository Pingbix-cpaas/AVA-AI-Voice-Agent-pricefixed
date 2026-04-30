import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from services import user_store_db as user_store
from services.security import hash_password, verify_password


# Configuration
DEFAULT_DEV_SECRET = "dev-secret-key-change-in-prod"
PLACEHOLDER_SECRETS = {
    "",
    "change-me-please",
    "changeme",
    DEFAULT_DEV_SECRET,
}

_raw_secret = (os.getenv("JWT_SECRET", "") or "").strip()
SECRET_KEY = _raw_secret or DEFAULT_DEV_SECRET
USING_PLACEHOLDER_SECRET = SECRET_KEY in PLACEHOLDER_SECRETS
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool = False


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: str = "platform"
    workspace_id: str = "platform-workspace"
    role: str = "end_user"
    status: str = "active"
    permissions: List[str] = []
    disabled: Optional[bool] = None
    must_change_password: Optional[bool] = False
    parent_user_id: Optional[str] = None
    permission_group: Optional[str] = "default"
    permission_scope: Optional[dict] = None


class UserInDB(User):
    password_hash: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# --- Helper Functions ---

def get_password_hash(password: str) -> str:
    return hash_password(password)


def load_users():
    return user_store.list_users()


def save_users(users):
    # Not needed with database - users are saved automatically
    pass


def get_user(username: str):
    user_dict = user_store.get_user_by_username(username)
    if user_dict:
        normalized = user_dict.copy()
        if "password_hash" not in normalized and "hashed_password" in normalized:
            normalized["password_hash"] = normalized["hashed_password"]
        return UserInDB(**normalized)
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None or user.status == "disabled" or user.disabled:
        raise credentials_exception
    return user


# --- Routes ---

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == "disabled" or user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    must_change = user.must_change_password or False
    user_store.record_login(user.username)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "workspace_id": user.workspace_id,
            "role": user.role,
            "permissions": user.permissions,
            "parent_user_id": user.parent_user_id,
            "permission_group": user.permission_group,
            "permission_scope": user.permission_scope or {},
        },
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer", "must_change_password": must_change}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    user_dict = user_store.get_user_by_username(current_user.username)

    if not user_dict:
        raise HTTPException(status_code=404, detail="User not found")

    password_hash = user_dict.get("password_hash")
    if not password_hash or not verify_password(request.old_password, password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    user_store.reset_password(current_user.username, request.new_password, must_change_password=False)

    return {"status": "success", "message": "Password updated successfully"}


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
