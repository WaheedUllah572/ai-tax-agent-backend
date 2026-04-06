from enum import Enum

class Stage(str, Enum):
    GREETING = "greeting"
    COUNTRY = "country"
    FILING_TYPE = "filing_type"
    TOPIC = "topic"
    ASSIST = "assist"
    CONFIRM_REMINDER = "confirm_reminder"

SESSIONS = {}

def get_session(session_id: str):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "stage": Stage.GREETING,
            "country": None,
            "filing_type": None,
            "topic": None,
            "pending_reminder": None,

            # ✅ NEW (for expense review system)
            "pending_receipt_review": None
        }
    return SESSIONS[session_id]