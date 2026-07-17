from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional
from enum import Enum
import re
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from models.storage import get_settings
from openai import OpenAI
from services.help_knowledge import HELP_KNOWLEDGE
from routes.mileage_routes import start_mileage_tracking, stop_mileage_tracking
from routes.calendar_routes import create_calendar_event_direct
router = APIRouter(tags=["Chatbot"])

# ✅ OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =====================================================
# SESSION MODEL
# =====================================================
class Stage(str, Enum):
    GREETING = "greeting"


class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "tax"
    session_id: Optional[str] = "default"


SESSIONS: Dict[str, Dict] = {}


def create_new_session():
    return {
        "stage": Stage.GREETING,
        "trip_details": {},
        "pending_trip_confirmation": None,
        "awaiting_trip_edit": False,
    }


def get_session(session_id: str) -> Dict:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = create_new_session()
    return SESSIONS[session_id]


# =====================================================
# 🧠 INTENT ENGINE
# =====================================================
def detect_intent(msg: str) -> Optional[str]:
    msg = msg.lower()

    start_keywords = [
    "start mileage",
    "start mile",
    "start trip",
    "start tracking",
    "begin trip",
    "begin mileage",
    "driving",
    "i am driving",
    "i'm driving",
]

    stop_keywords = [
        "arrived",
        "trip finished",
        "stop trip",
        "stop mileage",
        "end trip",
    ]

    schedule_keywords = [
    "schedule",
    "book meeting",
    "create meeting",
    "set appointment"
]

    if any(k in msg for k in start_keywords):
        return "start_mileage"

    if any(k in msg for k in stop_keywords):
        return "stop_mileage"
    
    if any(k in msg for k in schedule_keywords):
     return "schedule_meeting"

    return None


# =====================================================
# 🧠 SAFE ENTITY EXTRACTION
# =====================================================
def extract_trip_entities(msg: str) -> Dict:
    destination = None
    client_name = None
    purpose = None

    dest_match = re.search(
        r"to\s+(.*?)\s+(?=to meet|meet|about|$)",
        msg,
        re.IGNORECASE
    )
    if dest_match:
        destination = dest_match.group(1).strip()

    client_match = re.search(
        r"meet\s+(.*?)\s+(?=about|$)",
        msg,
        re.IGNORECASE
    )
    if client_match:
        client_name = client_match.group(1).strip()

    purpose_match = re.search(
        r"about\s+(.*)",
        msg,
        re.IGNORECASE
    )
    if purpose_match:
        purpose = purpose_match.group(1).strip()

    return {
    "destination": destination,
    "client_name": client_name,
    "purpose": purpose,

    "start_location": "Current Location",

    "business_name": destination,

    "meeting_with": client_name,

    "notes": None
}

def extract_schedule_details(msg: str):
    msg_lower = msg.lower()

    title = "New Meeting"

    person_match = re.search(
        r"with\s+([a-zA-Z\s]+?)(?:\s+today|\s+tomorrow|\s+at|$)",
        msg,
        re.IGNORECASE
    )

    if person_match:
        title = f"Meeting with {person_match.group(1).strip()}"

    settings = get_settings()
    user_timezone = settings.get(
        "timezone",
        "Asia/Karachi"
    )

    now = datetime.now(
        ZoneInfo(user_timezone)
    )

    # Default = today
    target_date = now.date()

    if "tomorrow" in msg_lower:
        target_date = now.date() + timedelta(days=1)

    elif "today" in msg_lower:
        target_date = now.date()

    # Time parser
    time_match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        msg_lower
    )

    hour = 17
    minute = 0

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridian = time_match.group(3)

        if meridian == "pm" and hour != 12:
            hour += 12

        if meridian == "am" and hour == 12:
            hour = 0

    start = datetime.combine(
    target_date,
    datetime.min.time(),
    tzinfo=ZoneInfo(user_timezone)
).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    end = start + timedelta(hours=1)

    return {
    "title": title,
    "start": start.isoformat(),
    "end": end.isoformat()
}


# =====================================================
# MAIN ENGINE
# =====================================================
def generate_reply(
    message: str,
    session: Dict,
    session_id: str,
    mode: str = "tax"
) -> str:

    msg = message.strip()
    intent = detect_intent(msg)

    # ==========================================
    # START MILEAGE
    # ==========================================

    if intent == "start_mileage":

     entities = extract_trip_entities(msg)

     session["pending_trip_confirmation"] = entities

     return (
    "🚗 I found the following trip information:\n\n"

    f"📍 Destination: {entities.get('destination') or 'Not specified'}\n"
    f"👤 Meeting With: {entities.get('client_name') or 'Not specified'}\n"
    f"📝 Purpose: {entities.get('purpose') or 'Not specified'}\n\n"

    "Please review your trip before tracking begins.\n\n"

    "Click CONFIRM to start mileage or EDIT to make changes."
)

    # EDIT
    # EDIT
    if msg.lower() == "edit" and session.get("pending_trip_confirmation"):

        session["awaiting_trip_edit"] = True

        return (
            "Please tell me the corrected trip.\n\n"
            "Example:\n"
            "I'm driving to ABC Plumbing to meet John about tax planning."
        )

    if session.get("awaiting_trip_edit"):

        entities = extract_trip_entities(msg)

        if (
            entities.get("destination")
            and entities.get("client_name")
            and entities.get("purpose")
        ):
            session["pending_trip_confirmation"] = entities

        session["awaiting_trip_edit"] = False

        return (
            "🚗 Updated trip detected.\n\n"
            f"📍 Destination: {session['pending_trip_confirmation']['destination']}\n"
            f"👤 Meeting: {session['pending_trip_confirmation']['client_name']}\n"
            f"📝 Purpose: {session['pending_trip_confirmation']['purpose']}\n\n"
            "Click CONFIRM to start mileage or EDIT to modify."
        )

    # CONFIRM
    if msg.lower() == "confirm" and session.get("pending_trip_confirmation"):

        entities = session["pending_trip_confirmation"]

        # Validate trip details
        if (
            not entities.get("destination")
            or not entities.get("client_name")
            or not entities.get("purpose")
        ):
            return (
                "⚠️ Trip details are incomplete.\n\n"
                "Please click EDIT and enter the complete trip before confirming."
            )

        # Start mileage tracking
        if not start_mileage_tracking(trip_meta=entities):
            return "⚠️ Mileage tracking already running."

        session["trip_details"] = entities
        session["pending_trip_confirmation"] = None
        session["awaiting_trip_edit"] = False

        return (
            "✅ Mileage tracking has started.\n\n"

            f"📍 Destination: {entities['destination']}\n"
            f"👤 Meeting: {entities['client_name']}\n"
            f"📝 Purpose: {entities['purpose']}\n\n"

            "I'm now tracking your business trip.\n\n"

            "When you arrive simply type:\n"

            "'Stop mileage'"
        )

    # STOP
    if intent == "stop_mileage":
        result = stop_mileage_tracking()

        if not result:
            return "⚠️ No active trip to stop."

        return (
    "✅ Mileage tracking stopped.\n\n"
    "Your business trip has been saved successfully.\n\n"
    f"📍 Distance: {result['distance_miles']} miles\n"
    f"⏱ Duration: {result['duration_minutes']} minutes\n"
    f"💰 Tax Deduction: ${result['deductible_amount']}"
)

    # SCHEDULE
    if intent == "schedule_meeting":
        details = extract_schedule_details(msg)

        response = create_calendar_event_direct(
            details["title"],
            details["start"],
            details["end"]
        )

        if response.get("success"):
            return (
                f"✅ Scheduled: {details['title']}\n"
                f"Start: {details['start']}"
            )

        return "⚠️ Could not create meeting."  
    # =================================================
    # 🤖 AI RESPONSE
    # =================================================
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content":
                        (
                            "You are Max, RefundPilot's app help assistant."
                            "Only answer questions about how to use RefundPilot features."
                            "If the user asks tax/legal/accounting questions, tell them to switch to Tax Assistant mode.\n\n"
                            + HELP_KNOWLEDGE
                        )
                        if mode == "help"
                        else
                        "You are Max, RefundPilot's AI business assistant helping users manage receipts, mileage, bookkeeping and taxes."
                },
                {"role": "user", "content": msg}
            ],
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI ERROR:", e)
        return "Sorry, I couldn’t process that. Please try again."


# =====================================================
# API
# =====================================================
@router.post("/chat")
async def chat(data: ChatRequest):
    session = get_session(data.session_id)
    reply = generate_reply(
    data.message,
    session,
    data.session_id,
    data.mode
)
    return {
        "reply": reply,
        "context": session
    }