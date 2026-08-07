# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import hashlib
import secrets
import json
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from .database import get_db
from ..models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """安全地验证密码，对异常哈希格式进行容错处理。"""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 2:
            return False
        salt, stored_hash = parts
        if not salt or not stored_hash:
            return False
        return hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex() == stored_hash
    except (ValueError, AttributeError, TypeError):
        return False

def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f'{salt}${pwd_hash}'

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user

def require_role(*roles):
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有权限执行此操作"
            )
        return current_user
    return role_checker


DATA_PERMISSION_MODULES = ("category", "brand", "product")
DATA_PERMISSION_ACTIONS = ("add", "edit", "delete")


def has_data_permission(current_user: User, module: str, action: str) -> bool:
    """账号级数据权限校验（同步，读 current_user.data_permissions JSON）。
    - 老板端恒有全部权限
    - data_permissions 如 {"category":["add"],"brand":["add","edit"],"product":["delete"]}
    - 未授权（空/缺失/不含该操作）一律 False
    """
    if current_user.role == "boss":
        return True
    if module not in DATA_PERMISSION_MODULES or action not in DATA_PERMISSION_ACTIONS:
        return False
    raw = getattr(current_user, "data_permissions", None)
    if not raw:
        return False
    try:
        perms = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return False
    actions = perms.get(module) or []
    return action in actions


def ensure_data_permission(current_user: User, module: str, action: str):
    """接口内使用：无权限直接抛 403。"""
    if not has_data_permission(current_user, module, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"您没有权限执行此操作（{module}.{action}）"
        )
