"""
Analytic AI — Auth Router (Firebase Authentication)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import firebase_admin
from firebase_admin import auth as firebase_auth

from core.database import get_db
from models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — verify Firebase ID token and return User record.
    Creates the user on first login.
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )

    token = creds.credentials

    # Check if Firebase is initialized
    if not firebase_admin._apps:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured. Set FIREBASE_CREDENTIALS env var on Render.",
        )

    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        print(f"DIAGNOSTIC: Firebase token verification failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}")

    uid = decoded.get("uid")
    email = decoded.get("email", "")
    name = decoded.get("name") or decoded.get("display_name") or email.split("@")[0]

    # Find or create user
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(firebase_uid=uid, email=email, display_name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"DIAGNOSTIC: Created new user {user.id} for Firebase UID {uid}")

    return user


@router.get("/me", tags=["Authentication"])
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
    }
