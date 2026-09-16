import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "super-secret-enterprise-key-for-ticket-system"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

import bcrypt
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        kullanici_adi: str = payload.get("sub")
        rol: str = payload.get("rol")
        ad_soyad: str = payload.get("ad_soyad")
        birim: str = payload.get("birim")
        if kullanici_adi is None:
            raise HTTPException(status_code=401, detail="Geçersiz yetkilendirme bilgisi")
        return {"kullanici_adi": kullanici_adi, "rol": rol, "ad_soyad": ad_soyad, "birim": birim}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token veya süresi dolmuş")
