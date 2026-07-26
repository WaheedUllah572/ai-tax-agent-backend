from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from calendar_utils import (
    save_calendar_tokens,
    load_calendar_tokens
)
from datetime import datetime, timezone
from fastapi import Depends
from dependencies.auth_dependency import get_current_user
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

@router.get("/status")
async def calendar_status(
    current_user=Depends(get_current_user)
):
    tokens = load_calendar_tokens()

    return {
        "connected": tokens is not None
    }

@router.get("/callback")
async def calendar_callback(
    request: Request
):

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
async def get_calendar_events(
    current_user=Depends(get_current_user)
):

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
async def create_event(
    data: CreateEventRequest,
    current_user=Depends(get_current_user)
):

    tokens = load_calendar_tokens()

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
        "dateTime": data.start,
        "timeZone": "Asia/Karachi"
    },
    "end": {
        "dateTime": data.end,
        "timeZone": "Asia/Karachi"
    }
}

    response = requests.post(
    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
    headers=headers,
    json=event_body
)

    print("CALENDAR STATUS:", response.status_code)
    print("CALENDAR RESPONSE:", response.text)

    return {
        "success": True,
        "event": response.json()
    }

def create_calendar_event_direct(title, start, end):

    tokens = load_calendar_tokens()

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

def check_upcoming_meetings():

    tokens = load_calendar_tokens()

    if not tokens:
        return {
            "connected": False,
            "reminders": []
        }

    access_token = tokens.get("access_token")

    if not access_token:
        return {
            "connected": False,
            "reminders": []
        }

    now = datetime.now(timezone.utc)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers=headers,
        params={
            "maxResults": 20,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": now.isoformat(),
            "showDeleted": False
        },
        timeout=15
    )

    if response.status_code != 200:
        print(
            "CALENDAR REMINDER ERROR:",
            response.status_code,
            response.text
        )

        return {
            "connected": True,
            "reminders": []
        }

    events = response.json().get("items", [])

    reminders = []

    for event in events:

        if event.get("eventType") == "birthday":
            continue

        start_data = event.get("start", {})
        start_value = start_data.get("dateTime")

        # Ignore all-day events
        if not start_value:
            continue

        try:
            event_start = datetime.fromisoformat(
                start_value.replace("Z", "+00:00")
            )

            if event_start.tzinfo is None:
                event_start = event_start.replace(
                    tzinfo=timezone.utc
                )

            minutes_until = (
                event_start.astimezone(timezone.utc) - now
            ).total_seconds() / 60

        except Exception as e:
            print(
                "CALENDAR DATE ERROR:",
                str(e)
            )
            continue

        # V1:
        # Only remind for events starting within
        # the next 60 minutes.
        if 0 <= minutes_until <= 60:

            reminders.append({
                "event_id": event.get("id"),
                "title": event.get(
                    "summary",
                    "Upcoming meeting"
                ),
                "start": start_value,
                "location": event.get(
                    "location",
                    ""
                ),
                "minutes_until": round(
                    minutes_until
                )
            })

    return {
        "connected": True,
        "reminders": reminders
    }


@router.get("/mileage-reminders")
async def calendar_mileage_reminders(
    current_user=Depends(get_current_user)
):

    return check_upcoming_meetings()