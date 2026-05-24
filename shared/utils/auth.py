import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

bearer_scheme = HTTPBearer()


class TokenData(BaseModel):
    user_id: str
    role: str

def verify_token(secret: str, token: str) -> TokenData:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return TokenData(user_id=payload["sub"], role=payload["role"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )