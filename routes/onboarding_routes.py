from fastapi import APIRouter, Body
from models.storage import get_settings, save_settings
from fastapi import Depends
from dependencies.auth_dependency import get_current_user
router = APIRouter(
    prefix="/onboarding",
    tags=["Onboarding"]
)

@router.post("/setup")
async def setup_business(
    data: dict = Body(...),
    current_user=Depends(get_current_user)
):

    settings = get_settings()

    settings["business_name"] = data.get("business_name")
    settings["business_type"] = data.get("business_type")
    settings["timezone"] = data.get("timezone")
    settings["account_count"] = data.get("account_count", 1)
    settings["onboarding_completed"] = True

    save_settings(settings)

    return {
        "success": True,
        "profile": settings
    }


@router.get("/profile")
async def get_profile(
    current_user=Depends(get_current_user)
):
    return get_settings()