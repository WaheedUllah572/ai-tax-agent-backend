from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional
from enum import Enum
import re
import os
from datetime import datetime, timedelta
import requests
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
        "driving",
        "start trip",
        "start tracking",
        "begin trip",
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
        "notes": None
    }

def extract_schedule_details(msg: str):

    title = "New Meeting"

    if "with" in msg:
        person = msg.split("with")[-1].strip()
        title = f"Meeting with {person}"

    start = datetime.utcnow() + timedelta(days=1)

    start = start.replace(
        hour=17,
        minute=0,
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

    # START MILEAGE
    if intent == "start_mileage" and not session.get("awaiting_trip_edit"):
        entities = extract_trip_entities(msg)
        session["pending_trip_confirmation"] = entities

        return (
            "🚗 I detected a new trip.\n\n"
            f"Destination: {entities.get('destination') or 'Not specified'}\n"
            f"Client: {entities.get('client_name') or 'Not specified'}\n"
            f"Purpose: {entities.get('purpose') or 'Not specified'}\n\n"
            "Type CONFIRM to start or EDIT to modify."
        )

    # EDIT
    if msg.lower() == "edit" and session.get("pending_trip_confirmation"):
        session["pending_trip_confirmation"] = None
        session["awaiting_trip_edit"] = True
        return "Please type the corrected trip sentence."

    if session.get("awaiting_trip_edit"):
        entities = extract_trip_entities(msg)
        session["pending_trip_confirmation"] = entities
        session["awaiting_trip_edit"] = False

        return (
            "🚗 Updated trip detected.\n\n"
            f"Destination: {entities.get('destination') or 'Not specified'}\n"
            f"Client: {entities.get('client_name') or 'Not specified'}\n"
            f"Purpose: {entities.get('purpose') or 'Not specified'}\n\n"
            "Type CONFIRM to start or EDIT to modify."
        )

    # CONFIRM
    if msg.lower() == "confirm" and session.get("pending_trip_confirmation"):
        entities = session["pending_trip_confirmation"]

        if not start_mileage_tracking(trip_meta=entities):
            return "⚠️ Mileage tracking already running."

        session["trip_details"] = entities
        session["pending_trip_confirmation"] = None
        session["awaiting_trip_edit"] = False

        return "✅ Trip confirmed and tracking started."

    # STOP
    if intent == "stop_mileage":
        result = stop_mileage_tracking()

        if not result:
            return "⚠️ No active trip to stop."

        return (
            "🛑 Trip completed and saved.\n\n"
            f"Trip ID: {result['trip_id']}\n"
            f"Distance: {result['distance_miles']} miles\n"
            f"Duration: {result['duration_minutes']} minutes"
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

    # AI RESPONSE
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are Max, an AI tax assistant."
                },
                {
                    "role": "user",
                    "content": msg
                }
            ],
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI ERROR:", e)
        return "Sorry, I couldn’t process that."  
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
                            "You are Max, TaxMate's app help assistant. "
                            "Only answer questions about how to use TaxMate features. "
                            "If the user asks tax/legal/accounting questions, tell them to switch to Tax Assistant mode.\n\n"
                            + HELP_KNOWLEDGE
                        )
                        if mode == "help"
                        else
                        "You are Max, an AI tax assistant helping users with taxes, expenses, and bookkeeping."
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