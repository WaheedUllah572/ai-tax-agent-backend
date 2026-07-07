from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import pyotp
import qrcode
import base64
from io import BytesIO

router = APIRouter(prefix="/auth", tags=["Auth"])

USERS_DB = "users.json"


def load_users():
    try:
        with open(USERS_DB, "r") as f:
            return json.load(f)
    except:
        return []


def save_users(data):
    with open(USERS_DB, "w") as f:
        json.dump(data, f, indent=4)


# -----------------------------
# Pydantic Models (Fix 400 Error)
# -----------------------------
class RegisterModel(BaseModel):
    name: str
    email: str
    password: str
    role: str = "business_owner"


class LoginModel(BaseModel):
    email: str
    password: str


class TwoFAVerifyModel(BaseModel):
    email: str
    code: str


class TwoFAEnableModel(BaseModel):
    email: str


# REGISTER
@router.post("/register")
def register(data: RegisterModel):
    users = load_users()

    if any(u["email"] == data.email for u in users):
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = {
    "name": data.name,
    "email": data.email,
    "password": data.password,
    "role": data.role,
    "2fa_enabled": False,
    "2fa_secret": None
}

    users.append(new_user)
    save_users(users)

    return {"message": "Registration success"}


# LOGIN
@router.post("/login")
def login(data: LoginModel):
    users = load_users()
    user = next((u for u in users if u["email"] == data.email and u["password"] == data.password), None)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if user["2fa_enabled"]:
        return {
    "2fa_required": True,
    "email": data.email,
    "role": user.get("role", "owner"),
    "name": user["name"]
}

    return {
    "login_success": True,
    "email": data.email,
    "role": user.get("role", "owner"),
    "name": user["name"]
}


# ENABLE 2FA
@router.post("/enable-2fa")
def enable_2fa(data: TwoFAEnableModel):
    users = load_users()
    user = next((u for u in users if u["email"] == data.email), None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    secret = pyotp.random_base32()
    user["2fa_secret"] = secret
    user["2fa_enabled"] = True
    save_users(users)

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=data.email, issuer_name="TaxMate AI")

    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return {"qr_code": qr_b64, "secret": secret}


# VERIFY 2FA
@router.post("/verify-2fa")
def verify_2fa(data: TwoFAVerifyModel):
    users = load_users()
    user = next((u for u in users if u["email"] == data.email), None)

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if not user["2fa_enabled"]:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    totp = pyotp.TOTP(user["2fa_secret"])

    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    return {
    "login_success": True,
    "email": data.email,
    "name": user["name"],
    "role": user.get("role", "business_owner")
}
