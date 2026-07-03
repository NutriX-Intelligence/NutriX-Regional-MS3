import os
import datetime
import logging
import jwt
import httpx
import bcrypt
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger("auth_service")

# JWT configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "nutrix-super-secret-key-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days session persistence

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Return payload if expired claim is valid
        return decoded_token
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token signature has expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None

async def verify_google_id_token(id_token: str) -> Dict[str, Any]:
    """Verify Google Oauth ID Token. Uses direct Google TokenInfo endpoint.
    
    Includes a fallback/mock block for emulator testing.
    """
    # 1. Check for mock token to ease testing
    if id_token.startswith("mock-google-"):
        email = id_token.replace("mock-google-", "") + "@example.com"
        name = id_token.replace("mock-google-", "").capitalize()
        return {
            "email": email,
            "name": name,
            "sub": f"mock-sub-{id_token}",
            "picture": "https://www.gravatar.com/avatar/"
        }

    # 2. Query Google's verification service
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                logger.error(f"Google tokeninfo API failed with code {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google ID Token (verification failed on Google servers)."
                )
            payload = response.json()
            # Verify issuer is Google
            if payload.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer."
                )
            return payload
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.error(f"Error calling Google OAuth info endpoint: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OAuth verification server unreachable: {str(e)}"
            )
