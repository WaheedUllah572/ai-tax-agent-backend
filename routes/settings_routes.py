from fastapi import APIRouter, Body

from models.storage import (
    get_settings,
    save_settings
)

router = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)


@router.get("/")
async def get_user_settings():

    return get_settings()


@router.put("/")
async def update_settings(
    data: dict = Body(...)
):

    settings = get_settings()

    settings["jurisdiction"] = data.get(
        "jurisdiction",
        "US"
    )

    save_settings(settings)

    return {
        "success": True,
        "settings": settings
    }