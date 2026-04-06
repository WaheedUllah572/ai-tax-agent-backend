from datetime import datetime

REMINDERS = []  # later → DB / Redis / Cron

def create_reminder(session_id: str, message: str, remind_at: str):
    reminder = {
        "session_id": session_id,
        "message": message,
        "remind_at": remind_at,
        "created_at": datetime.utcnow().isoformat(),
        "status": "scheduled",
    }
    REMINDERS.append(reminder)
    return reminder