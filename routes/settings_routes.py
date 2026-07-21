from fastapi import APIRouter, Body
from fastapi import Depends
from dependencies.auth_dependency import get_current_user
from models.storage import (
    get_settings,
    save_settings
)

router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)


@router.get("/")
async def get_user_settings(
    current_user=Depends(get_current_user)
):

    return get_settings()


@router.put("/")
async def update_settings(
    data: dict = Body(...),
    current_user=Depends(get_current_user)
):

    settings = get_settings()

    settings["jurisdiction"] = data.get(
        "jurisdiction",
        settings.get("jurisdiction", "US")
    )

    settings["business_name"] = data.get(
        "business_name",
        settings.get("business_name", "")
    )

    settings["business_type"] = data.get(
        "business_type",
        settings.get("business_type", "")
    )

    settings["country"] = data.get(
    "country",
    settings.get("country", "United States")
)

    settings["account_count"] = data.get(
        "account_count",
        settings.get("account_count", 1)
    )

    settings["calendar_connected"] = data.get(
        "calendar_connected",
        settings.get("calendar_connected", False)
    )

    settings["gmail_connected"] = data.get(
        "gmail_connected",
        settings.get("gmail_connected", False)
    )

    settings["xero_connected"] = data.get(
        "xero_connected",
        settings.get("xero_connected", False)
    )

    save_settings(settings)

    return {
        "success": True,
        "settings": settings
    }