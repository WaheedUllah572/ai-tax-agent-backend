import json
import os
import re

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
)

from pydantic import BaseModel

from openai import OpenAI

from models.storage import get_settings

from dependencies.auth_dependency import (
    get_current_user,
)

from services.help_knowledge import (
    HELP_KNOWLEDGE,
)

from routes.mileage_routes import (
    start_mileage_tracking,
    stop_mileage_tracking,
)

from routes.calendar_routes import (
    create_calendar_event_direct,
)


router = APIRouter(
    tags=["Chatbot"]
)


# =========================================================
# OPENAI
# =========================================================

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)


# =========================================================
# SESSION MODEL
# =========================================================

class Stage(str, Enum):

    GREETING = "greeting"


class ChatRequest(BaseModel):

    message: str

    mode: Optional[str] = "tax"

    session_id: Optional[str] = "default"

    start_location: Optional[Dict] = None

    # NEW:
    # Current GPS when stopping the trip.
    end_location: Optional[Dict] = None


SESSIONS: Dict[
    str,
    Dict
] = {}


# =========================================================
# CREATE SESSION
# =========================================================

def create_new_session():

    return {

        "stage":
            Stage.GREETING,

        "trip_details":
            {},

        "pending_trip_confirmation":
            None,

        "awaiting_trip_edit":
            False,
    }


# =========================================================
# AI TRIP ENTITY EXTRACTION
# =========================================================

def extract_trip_entities_ai(
    msg: str
) -> Dict:

    response = client.chat.completions.create(

        model="gpt-4o-mini",

        temperature=0,

        response_format={
            "type":
                "json_object"
        },

        messages=[

            {
                "role":
                    "system",

                "content":
                    """
You extract business trip information from
natural language.

Return ONLY valid JSON.

Schema:

{
    "destination": null,
    "client_name": null,
    "purpose": null
}

Rules:

- Extract only information explicitly present
  in the user's message.
- Do not invent a destination.
- Do not invent a person's name.
- Do not invent a purpose.
- If information is missing, return null.
- Do not return markdown.
- Do not explain anything.
""",
            },

            {
                "role":
                    "user",

                "content":
                    msg,
            },

        ],
    )

    try:

        data = json.loads(
            response
            .choices[0]
            .message
            .content
        )

    except Exception as e:

        print(
            "TRIP ENTITY JSON ERROR:",
            e,
        )

        data = {}

    destination = data.get(
        "destination"
    )

    client_name = data.get(
        "client_name"
    )

    purpose = data.get(
        "purpose"
    )

    return {

        "destination":
            destination,

        "client_name":
            client_name,

        "purpose":
            purpose,

        "start_location":
            None,

        "business_name":
            destination,

        "meeting_with":
            client_name,

        "notes":
            None,
    }


# =========================================================
# SESSION
# =========================================================

def get_session(
    session_id: str
) -> Dict:

    if session_id not in SESSIONS:

        SESSIONS[
            session_id
        ] = create_new_session()

    return SESSIONS[
        session_id
    ]


# =========================================================
# INTENT ENGINE
# =========================================================

def detect_intent(
    msg: str
) -> Optional[str]:

    msg = msg.lower().strip()

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    start_patterns = [

        "start mileage",

        "start my mileage",

        "start trip",

        "start my trip",

        "start a trip",

        "start my journey",

        "begin trip",

        "begin my trip",

        "begin a trip",

        "begin mileage",

        "begin my mileage",

        "track mileage",

        "track my mileage",

        "track this trip",

        "start tracking",

        "start tracking mileage",

        "i'm driving",

        "i am driving",

        "driving to",

        "heading to",

        "headed to",

        "going to",

        "i'm going to",

        "i am going to",

        "on my way",

        "leaving for",

        "leave for",
    ]

    # -----------------------------------------------------
    # STOP
    # -----------------------------------------------------

    stop_patterns = [

        "stop trip",

        "stop mileage",

        "end trip",

        "finish trip",

        "trip finished",

        "arrived",

        "i'm here",

        "i am here",

        "finished driving",

        "done driving",
    ]

    # -----------------------------------------------------
    # CALENDAR
    # -----------------------------------------------------

    schedule_patterns = [

        "schedule",

        "book meeting",

        "create meeting",

        "set appointment",
    ]

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Check STOP before START.
    #
    # -----------------------------------------------------

    for pattern in stop_patterns:

        if pattern in msg:

            return "stop_mileage"

    for pattern in start_patterns:

        if pattern in msg:

            return "start_mileage"

    for pattern in schedule_patterns:

        if pattern in msg:

            return "schedule_meeting"

    return None


# =========================================================
# SCHEDULE EXTRACTION
# =========================================================

def extract_schedule_details(
    msg: str
):

    msg_lower = msg.lower()

    title = "New Meeting"

    person_match = re.search(

        r"with\s+([a-zA-Z\s]+?)"
        r"(?:\s+today|\s+tomorrow|\s+at|$)",

        msg,

        re.IGNORECASE,
    )

    if person_match:

        title = (
            "Meeting with "
            +
            person_match
            .group(1)
            .strip()
        )

    settings = get_settings()

    user_timezone = settings.get(
        "timezone",
        "Asia/Karachi",
    )

    now = datetime.now(
        ZoneInfo(
            user_timezone
        )
    )

    target_date = now.date()

    if "tomorrow" in msg_lower:

        target_date = (
            now.date()
            +
            timedelta(days=1)
        )

    elif "today" in msg_lower:

        target_date = (
            now.date()
        )

    time_match = re.search(

        r"(\d{1,2})"
        r"(?::(\d{2}))?"
        r"\s*(am|pm)",

        msg_lower,
    )

    hour = 17

    minute = 0

    if time_match:

        hour = int(
            time_match.group(1)
        )

        minute = int(
            time_match.group(2)
            or 0
        )

        meridian = (
            time_match.group(3)
        )

        if (
            meridian == "pm"
            and hour != 12
        ):

            hour += 12

        if (
            meridian == "am"
            and hour == 12
        ):

            hour = 0

    start = datetime.combine(

        target_date,

        datetime.min.time(),

        tzinfo=ZoneInfo(
            user_timezone
        ),

    ).replace(

        hour=hour,

        minute=minute,

        second=0,

        microsecond=0,
    )

    end = (
        start
        +
        timedelta(hours=1)
    )

    return {

        "title":
            title,

        "start":
            start.isoformat(),

        "end":
            end.isoformat(),
    }


# =========================================================
# MAIN ENGINE
# =========================================================

def generate_reply(

    message: str,

    session: Dict,

    session_id: str,

    mode: str = "tax",

    start_location: Optional[Dict] = None,

    end_location: Optional[Dict] = None,

) -> str:

    msg = message.strip()

    # =====================================================
    # HELP
    # =====================================================

    if mode == "help":

        try:

            response = (
                client.chat.completions.create(

                    model="gpt-4o-mini",

                    messages=[

                        {
                            "role":
                                "system",

                            "content":
                                (
                                    "You are Max, "
                                    "RefundPilot's "
                                    "app help assistant. "

                                    "Only answer questions "
                                    "about how to use "
                                    "RefundPilot features. "

                                    "Explain where features "
                                    "are located and how "
                                    "to use them. "

                                    "Do not execute mileage "
                                    "tracking, calendar "
                                    "scheduling, or any "
                                    "other application action. "

                                    "If the user asks tax, "
                                    "legal, or accounting "
                                    "questions, tell them "
                                    "to switch to Tax Expert "
                                    "mode.\n\n"
                                    +
                                    HELP_KNOWLEDGE
                                ),
                        },

                        {
                            "role":
                                "user",

                            "content":
                                msg,
                        },

                    ],

                    max_tokens=300,
                )
            )

            return (
                response
                .choices[0]
                .message
                .content
                .strip()
            )

        except Exception as e:

            print(
                "HELP AI ERROR:",
                e,
            )

            return (
                "Sorry, I couldn't "
                "process that help "
                "request. Please try again."
            )

    # =====================================================
    # INTENT
    # =====================================================

    intent = detect_intent(
        msg
    )

    print(
        "CHAT MESSAGE:",
        msg,
    )

    print(
        "DETECTED INTENT:",
        intent,
    )

    # =====================================================
    # START MILEAGE
    # =====================================================

    if intent == "start_mileage":

        print(
            "========== "
            "TRIP START COMMAND "
            "DETECTED =========="
        )

        # -------------------------------------------------
        # Extract trip information
        # -------------------------------------------------

        entities = (
            extract_trip_entities_ai(
                msg
            )
        )

        # -------------------------------------------------
        # GPS
        # -------------------------------------------------

        if start_location is not None:

            entities[
                "start_location"
            ] = start_location

            print(
                "========== "
                "TRIP START GPS "
                "RECEIVED =========="
            )

            print(
                f"LATITUDE: "
                f"{start_location.get('latitude')}"
            )

            print(
                f"LONGITUDE: "
                f"{start_location.get('longitude')}"
            )

            print(
                f"ACCURACY: "
                f"{start_location.get('accuracy')}"
            )

            print(
                "========================"
            )

        else:

            print(
                "TRIP START GPS: "
                "NOT RECEIVED"
            )

        # -------------------------------------------------
        # Entities
        # -------------------------------------------------

        destination = (
            entities.get(
                "destination"
            )
        )

        client_name = (
            entities.get(
                "client_name"
            )
        )

        purpose = (
            entities.get(
                "purpose"
            )
        )

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        missing = []

        if not destination:

            missing.append(
                "destination"
            )

        if not client_name:

            missing.append(
                "who you're meeting"
            )

        if not purpose:

            missing.append(
                "business purpose"
            )

        # -------------------------------------------------
        # GPS REQUIRED
        # -------------------------------------------------

        if not start_location:

            missing.append(
                "your current GPS location"
            )

        # -------------------------------------------------
        # Missing information
        # -------------------------------------------------

        if missing:

            return (

                "Before I start "
                "mileage tracking, "
                "I still need "
                +
                ", ".join(
                    missing
                )
                +
                ". Please provide "
                "the missing information."
            )

        # -------------------------------------------------
        # START TRACKING
        # -------------------------------------------------

        started = (
            start_mileage_tracking(

                user_id=
                    session_id,

                trip_meta=
                    entities,
            )
        )

        if not started:

            return (

                "⚠️ Mileage tracking "
                "is already running. "

                "Say 'stop trip' "
                "to finish the "
                "current trip."
            )

        # -------------------------------------------------
        # SAVE SESSION
        # -------------------------------------------------

        session[
            "trip_details"
        ] = entities

        session[
            "pending_trip_confirmation"
        ] = None

        session[
            "awaiting_trip_edit"
        ] = False

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return (

            "✅ Mileage tracking "
            "has started.\n\n"

            f"📍 Destination: "
            f"{destination}\n"

            f"👤 Meeting With: "
            f"{client_name}\n"

            f"📝 Business Purpose: "
            f"{purpose}\n\n"

            "I'm tracking your "
            "trip using GPS. "

            "When you arrive, "
            "say 'stop trip'."
        )

    # =====================================================
    # STOP MILEAGE
    # =====================================================

    if intent == "stop_mileage":

        print(
            "========== "
            "TRIP STOP COMMAND "
            "DETECTED =========="
        )

        print(
            "END GPS:",
            end_location,
        )

        result = (
            stop_mileage_tracking(

                user_id=
                    session_id,

                end_location=
                    end_location,
            )
        )

        if not result:

            return (
                "⚠️ No active trip "
                "to stop."
            )

        if result.get(
            "error"
        ):

            return (
                "⚠️ "
                +
                result[
                    "error"
                ]
            )

        # -------------------------------------------------
        # Clear trip session
        # -------------------------------------------------

        session[
            "trip_details"
        ] = {}

        session[
            "pending_trip_confirmation"
        ] = None

        session[
            "awaiting_trip_edit"
        ] = False

        # -------------------------------------------------
        # Success
        # -------------------------------------------------

        return (

            "✅ Mileage tracking "
            "stopped.\n\n"

            "Your business trip "
            "has been saved "
            "successfully.\n\n"

            f"📍 Distance: "
            f"{result['distance_miles']} "
            f"miles\n"

            f"⏱ Duration: "
            f"{result['duration_minutes']} "
            f"minutes\n"

            f"💰 Tax Deduction: "
            f"${result['deductible_amount']:.2f}"
        )

    # =====================================================
    # SCHEDULE
    # =====================================================

    if intent == "schedule_meeting":

        details = (
            extract_schedule_details(
                msg
            )
        )

        response = (
            create_calendar_event_direct(

                details[
                    "title"
                ],

                details[
                    "start"
                ],

                details[
                    "end"
                ],
            )
        )

        if response.get(
            "success"
        ):

            return (

                f"✅ Scheduled: "
                f"{details['title']}\n"

                f"Start: "
                f"{details['start']}"
            )

        return (
            "⚠️ Could not "
            "create meeting."
        )

    # =====================================================
    # GENERAL AI
    # =====================================================

    try:

        response = (
            client.chat.completions.create(

                model="gpt-4o-mini",

                messages=[

                    {
                        "role":
                            "system",

                        "content":
                            (
                                "You are Max, "
                                "RefundPilot's "
                                "AI business assistant "
                                "helping users manage "
                                "receipts, mileage, "
                                "bookkeeping and taxes."
                            ),
                    },

                    {
                        "role":
                            "user",

                        "content":
                            msg,
                    },

                ],

                max_tokens=300,
            )
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        print(
            "AI ERROR:",
            e,
        )

        return (
            "Sorry, I couldn't "
            "process that. "
            "Please try again."
        )


# =========================================================
# CHAT API
# =========================================================

@router.post("/chat")
async def chat(

    data: ChatRequest,

    current_user=Depends(
        get_current_user
    ),

):

    user_id = str(
        current_user.id
    )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Never trust the client's session_id for ownership.
    #
    # Use authenticated user ID.
    # -----------------------------------------------------

    session = get_session(
        user_id
    )

    reply = generate_reply(

        message=data.message,

        session=session,

        session_id=user_id,

        mode=data.mode,

        start_location=
            data.start_location,

        end_location=
            data.end_location,
    )

    return {

        "reply":
            reply,

        "context":
            session,
    }


# =========================================================
# TRANSCRIBE
# =========================================================

@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...)
):

    try:

        audio_bytes = (
            await audio.read()
        )

        print(
            "Filename:",
            audio.filename,
        )

        print(
            "Content-Type:",
            audio.content_type,
        )

        print(
            "Size:",
            len(
                audio_bytes
            ),
        )

        transcript = (
            client.audio.transcriptions.create(

                model=
                    "gpt-4o-mini-transcribe",

                file=(

                    audio.filename,

                    audio_bytes,

                    audio.content_type,
                ),
            )
        )

        return {

            "text":
                transcript.text
        }

    except Exception as e:

        print(
            "TRANSCRIBE ERROR:",
            e,
        )

        raise