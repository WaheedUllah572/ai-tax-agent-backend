from fastapi import APIRouter
from datetime import datetime
import uuid
from typing import Optional, Dict

from models.storage import get_mileage, save_mileage

router = APIRouter(prefix="/mileage", tags=["Mileage"])

ACTIVE_TRIPS: Dict[str, Dict] = {}

IRS_MILEAGE_RATE = 0.67


def calculate_annual_miles(history):
    total = 0
    current_year = datetime.utcnow().year

    for trip in history:
        trip_date = trip.get("date", "")
        if trip_date.startswith(str(current_year)):
            total += trip.get("total_miles", 0)

    return round(total, 2)


def start_mileage_tracking(trip_meta: Optional[Dict] = None):
    if ACTIVE_TRIPS.get("current"):
        return False

    ACTIVE_TRIPS["current"] = {
    "start_time": datetime.utcnow(),
    "status": "In Progress",
    "created_by": "Max AI",
    "meta": trip_meta or {}
}

    return True


def stop_mileage_tracking():
    trip = ACTIVE_TRIPS.get("current")
    if not trip:
        return None

    end_time = datetime.utcnow()
    duration_minutes = (end_time - trip["start_time"]).total_seconds() / 60
    distance_miles = round(duration_minutes * 0.5, 2)

    meta = trip.get("meta", {})

    # IRS CALCULATIONS
    deductible_amount = round(distance_miles * IRS_MILEAGE_RATE, 2)

    history = get_mileage()
    annual_miles_total = calculate_annual_miles(history) + distance_miles

    trip_record = {
        "trip_id": str(uuid.uuid4()),
        "date": datetime.utcnow().date().isoformat(),
        "start_time": trip["start_time"].isoformat(),
        "end_time": end_time.isoformat(),
        "duration_minutes": round(duration_minutes, 1),
        "distance_miles": distance_miles,
        "trip_type": "business",
        "status": "Completed",

        # EXISTING FIELDS
        "destination": meta.get("destination"),
        "business_name": meta.get("business_name"),
        "client_name": meta.get("client_name"),
        "meeting_with": meta.get("meeting_with"),
        "purpose": meta.get("purpose"),
        "notes": meta.get("notes"),

        # IRS REQUIRED FIELDS
        "start_location": meta.get("start_location"),
        "end_location": meta.get("end_location"),
        "business_purpose": meta.get("purpose"),
        "odometer_start": meta.get("odometer_start"),
        "odometer_end": meta.get("odometer_end"),
        "total_miles": distance_miles,
        "irs_rate": IRS_MILEAGE_RATE,
        "deductible_amount": deductible_amount,
        "annual_miles_total": annual_miles_total,
        "method": "standard_mileage",
        "created_by": "Max AI",

        # AUDIT TRAIL
        "audit_log": [
    {
        "action": "trip_completed",
        "by": "Max AI",
        "date": datetime.utcnow().isoformat()
    }
]
    }

    history.append(trip_record)
    save_mileage(history)

    ACTIVE_TRIPS["current"] = None

    return trip_record


@router.post("/start")
async def start_mileage(meta: Dict = {}):
    if not start_mileage_tracking(meta):
        return {"error": "Mileage already running"}
    return {"status": "Mileage tracking started"}


@router.post("/stop")
async def stop_mileage():
    result = stop_mileage_tracking()
    if not result:
        return {"error": "No active trip"}
    return result


@router.get("/history")
async def get_trip_history():
    return get_mileage()