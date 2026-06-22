from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import os

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CALENDAR_REDIRECT_URI = os.getenv(
    "GOOGLE_CALENDAR_REDIRECT_URI"
)


@router.get("/connect")
async def connect_calendar():

    scope = "https://www.googleapis.com/auth/calendar.readonly"

    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_CALENDAR_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return RedirectResponse(url)