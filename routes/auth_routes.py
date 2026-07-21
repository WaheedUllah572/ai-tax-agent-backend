from fastapi import APIRouter, HTTPException, Depends
from dependencies.auth_dependency import get_current_user
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])

# =====================================================
# SUPABASE CONFIGURATION
# =====================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not configured")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY is not configured")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")


# Normal client used for authentication
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Admin client used only by backend
supabase_admin = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


# =====================================================
# REQUEST MODELS
# =====================================================

class RegisterModel(BaseModel):
    name: str
    email: str
    password: str


class LoginModel(BaseModel):
    email: str
    password: str


# =====================================================
# REGISTER BUSINESS OWNER
# =====================================================

@router.post("/register")
def register(data: RegisterModel):

    email = data.email.strip().lower()
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required"
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    try:
        # Create user through Supabase Auth.
        # Supabase handles password storage securely.
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": data.password,
        })

        user = auth_response.user

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Unable to create user account"
            )

        # Create RefundPilot profile.
        # Public registration is ALWAYS business_owner.
        profile = {
            "id": str(user.id),
            "name": name,
            "role": "business_owner",
        }

        supabase_admin.table(
            "profiles"
        ).insert(profile).execute()

        return {
            "success": True,
            "message": "Registration successful. Please login."
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "SUPABASE REGISTRATION ERROR:",
            str(e)
        )

        error_message = str(e).lower()

        if (
            "already registered" in error_message
            or "already exists" in error_message
        ):
            raise HTTPException(
                status_code=400,
                detail="User already exists"
            )

        raise HTTPException(
            status_code=400,
            detail="Registration failed"
        )


# =====================================================
# LOGIN
# =====================================================

@router.post("/login")
def login(data: LoginModel):

    email = data.email.strip().lower()

    try:
        # Supabase verifies the password.
        auth_response = (
            supabase.auth.sign_in_with_password({
                "email": email,
                "password": data.password,
            })
        )

        user = auth_response.user
        session = auth_response.session

        if not user or not session:
            raise HTTPException(
                status_code=400,
                detail="Invalid email or password"
            )

        # Get application profile
        profile_response = (
            supabase_admin
            .table("profiles")
            .select("*")
            .eq("id", str(user.id))
            .limit(1)
            .execute()
        )

        if not profile_response.data:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )

        profile = profile_response.data[0]

        return {
            "login_success": True,
            "email": user.email,
            "name": profile.get("name"),
            "role": profile.get(
                "role",
                "business_owner"
            ),

            # Needed later for authenticated API requests
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "SUPABASE LOGIN ERROR:",
            str(e)
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid email or password"
        )
    
    # =====================================================
# CURRENT AUTHENTICATED USER
# =====================================================

@router.get("/me")
def get_me(current_user=Depends(get_current_user)):

    return {
        "authenticated": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
    }