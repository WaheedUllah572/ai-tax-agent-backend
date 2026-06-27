from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from calendar_utils import (
    save_calendar_tokens,
    load_calendar_tokens
)
from datetime import datetime, timezone
from pydantic import BaseModel
import os
import requests

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"]
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_CALENDAR_REDIRECT_URI = os.getenv(
    "GOOGLE_CALENDAR_REDIRECT_URI"
)


@router.get("/connect")
async def connect_calendar():

    scope = "https://www.googleapis.com/auth/calendar"

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


@router.get("/callback")
async def calendar_callback(request: Request):

    code = request.query_params.get("code")

    if not code:
        return JSONResponse(
            {"error": "Missing code"},
            status_code=400
        )

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_CALENDAR_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    tokens = requests.post(
        token_url,
        data=data
    ).json()

    save_calendar_tokens(tokens)

    return {
    "success": True,
    "calendar_connected": True,
    "message": "Calendar connected successfully"
}

@router.get("/events")
async def get_calendar_events():

    tokens = load_calendar_tokens()

    if not tokens:
        return {
            "success": False,
            "message": "Calendar not connected"
        }

    access_token = tokens.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
        params={
            "maxResults": 10,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": datetime.now(
                timezone.utc
            ).isoformat(),
            "showDeleted": False
        }
    )

    events = response.json().get("items", [])

    filtered_events = []

    for event in events:

        if event.get("eventType") == "birthday":
            continue

        start = event.get("start", {})

        if "dateTime" not in start:
            continue

        filtered_events.append({
    "summary": event.get("summary"),
    "start": start.get("dateTime"),
    "timezone": start.get("timeZone")
})

    return {
        "success": True,
        "events": filtered_events
    }

class CreateEventRequest(BaseModel):
    title: str
    start: str
    end: str


@router.post("/create-event")
async def create_event(data: CreateEventRequest):

    tokens = load_tokens()

    if not tokens:
        return {
            "success": False,
            "message": "Calendar not connected"
        }

    access_token = tokens.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    event_body = {
        "summary": data.title,
        "start": {
            "dateTime": data.start
        },
        "end": {
            "dateTime": data.end
        }
    }

    response = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
        json=event_body
    )

    return {
        "success": True,
        "event": response.json()
    }

def create_calendar_event_direct(title, start, end):

    tokens = load_tokens()

    if not tokens:
        return {
            "success": False,
            "message": "Calendar not connected"
        }

    access_token = tokens.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    event_body = {
        "summary": title,
        "start": {
            "dateTime": start
        },
        "end": {
            "dateTime": end
        }
    }

    response = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
        json=event_body
    )

    return {
        "success": response.status_code in [200, 201],
        "event": response.json()
    }