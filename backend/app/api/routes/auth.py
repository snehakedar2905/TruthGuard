"""
TruthGuard User Authentication and Profile API Routes.

Provides Signup, Login, Token Verification, and Profile Update endpoints.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import UserRecord, get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH_SECRET = settings.secret_key or "truthguard-auth-secret-key-32bytes-secure"


# Password Utility
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, hashed_value: str) -> bool:
    if ":" not in hashed_value:
        return False
    salt, hashed = hashed_value.split(":", 1)
    test_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(hashed, test_hash)


def create_token(user_id: str, email: str) -> str:
    """Create a signed bearer session token."""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + (86400 * 7),  # 7 days
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload_str}.{signature}"
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """Validate and decode a session token."""
    try:
        payload_str, signature = token.rsplit(".", 1)
        expected_sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        if not secrets.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature.")
        payload = json.loads(payload_str)
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
        return payload
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization token.")


import random
import re

# Temporary in-memory phone OTP registry for contact validation
_PENDING_PHONE_OTPS: Dict[str, Dict[str, Any]] = {}


# Request & Response Schemas
class ContactValidationRequest(BaseModel):
    country_code: str = Field("+1", max_length=10)
    mobile_no: str = Field(..., min_length=1, max_length=30)


class ContactOTPVerifyRequest(BaseModel):
    country_code: str = Field("+1", max_length=10)
    mobile_no: str = Field(..., min_length=1, max_length=30)
    otp: str = Field(..., min_length=4, max_length=6)


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country_code: str = Field("+1", max_length=10)
    mobile_no: str = Field(..., min_length=7, max_length=30)
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=4)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=1)


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    country_code: Optional[str] = Field(None, max_length=10)
    mobile_no: Optional[str] = Field(None, max_length=30)


class AuthResponse(BaseModel):
    status: str = "success"
    message: str
    token: str
    user: Dict[str, Any]


class UserResponse(BaseModel):
    status: str = "success"
    user: Dict[str, Any]


# Dependency to get current user from Bearer header
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserRecord:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required.")
    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decode_token(token)
    user_id = payload.get("sub")
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    return user


from app.services.sms_service import sms_service


# Contact Validation & OTP Routes
@router.post("/send-contact-otp")
async def send_contact_otp(request: ContactValidationRequest):
    """Validate contact number format, dispatch SMS to mobile phone, and store OTP."""
    digits = re.sub(r"\D", "", request.mobile_no)
    if not digits or len(digits) < 7 or len(digits) > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact number must contain between 7 and 15 numeric digits without alphabets."
        )
    key = f"{request.country_code.strip()}:{digits}"
    otp = f"{random.randint(1000, 9999)}"
    _PENDING_PHONE_OTPS[key] = {"otp": otp, "expires_at": time.time() + 600}

    # Dispatch SMS to the user's mobile number
    sms_res = await sms_service.send_otp(request.country_code, digits, otp)

    formatted = f"{request.country_code.strip()} {digits}"
    return {
        "status": "success",
        "message": f"Verification code sent via SMS to {formatted}",
        "otp": otp,
        "formatted_number": formatted,
        "delivery_provider": sms_res.get("provider"),
        "carrier_delivered": bool(sms_res.get("provider") in ("twilio", "http_gateway")),
    }


@router.post("/verify-contact-otp")
async def verify_contact_otp(request: ContactOTPVerifyRequest):
    """Verify phone verification OTP code."""
    digits = re.sub(r"\D", "", request.mobile_no)
    key = f"{request.country_code.strip()}:{digits}"
    pending = _PENDING_PHONE_OTPS.get(key)
    if not pending or pending.get("expires_at", 0) < time.time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or was not requested. Please request a new code."
        )
    if pending.get("otp") != request.otp.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please check and try again."
        )
    _PENDING_PHONE_OTPS.pop(key, None)
    return {
        "status": "success",
        "verified": True,
        "message": "Contact number successfully verified."
    }


# Routes
@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register a new user account with validated country code and mobile number."""
    existing = db.query(UserRecord).filter(UserRecord.email == request.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    digits = re.sub(r"\D", "", request.mobile_no)
    if not digits or len(digits) < 7 or len(digits) > 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact number must contain between 7 and 15 numeric digits (alphabets are not allowed)."
        )

    new_user = UserRecord(
        name=request.name.strip(),
        country_code=request.country_code.strip() or "+1",
        mobile_no=digits,
        email=request.email.lower().strip(),
        password_hash=hash_password(request.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_token(new_user.id, new_user.email)
    return AuthResponse(
        message="Account successfully created.",
        token=token,
        user=new_user.to_dict(),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate existing user credentials and return session token."""
    user = db.query(UserRecord).filter(UserRecord.email == request.email.lower().strip()).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = create_token(user.id, user.email)
    return AuthResponse(
        message="Login successful.",
        token=token,
        user=user.to_dict(),
    )


@router.get("/verify", response_model=UserResponse)
async def verify_user(user: UserRecord = Depends(get_current_user)) -> UserResponse:
    """Verify session token and retrieve current authenticated user details."""
    return UserResponse(user=user.to_dict())


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    """Update profile details including name, country code, and mobile number."""
    if request.name is not None:
        user.name = request.name.strip()
    if request.country_code is not None:
        user.country_code = request.country_code.strip()
    if request.mobile_no is not None:
        user.mobile_no = re.sub(r"\D", "", request.mobile_no)

    db.commit()
    db.refresh(user)
    return UserResponse(user=user.to_dict())
