from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict
from pydantic import BaseModel

from dependencies.auth_dependency import get_current_user
from models.storage import get_mileage, save_mileage


router = APIRouter(prefix="/mileage", tags=["Mileage"])

ACTIVE_TRIPS: Dict[str, Dict] = {}

IRS_MILEAGE_RATE = 0.67


# =========================================================
# MODELS
# =========================================================

class ManualTripRequest(BaseModel):
    date: str
    start_location: str
    destination: str
    purpose: Optional[str] = "Business"
    miles: float
    method: Optional[str] = "manual"


# =========================================================
# HELPERS
# =========================================================

def calculate_annual_miles(history):
    total = 0
    current_year = datetime.utcnow().year

    for trip in history:
        trip_date = trip.get("date", "")

        if trip_date.startswith(str(current_year)):
            total += float(trip.get("total_miles", 0) or 0)

    return round(total, 2)


def start_mileage_tracking(trip_meta: Optional[Dict] = None):

    if ACTIVE_TRIPS.get("current"):
        return False

    ACTIVE_TRIPS["current"] = {
        "start_time": datetime.now(timezone.utc),
        "status": "In Progress",
        "created_by": "Max AI",
        "meta": trip_meta or {}
    }

    return True


def stop_mileage_tracking():

    trip = ACTIVE_TRIPS.get("current")

    if not trip:
        return None

    end_time = datetime.now(timezone.utc)

    duration_minutes = (
        end_time - trip["start_time"]
    ).total_seconds() / 60

    # Existing V1 estimation logic
    distance_miles = round(duration_minutes * 0.5, 2)

    meta = trip.get("meta", {})

    deductible_amount = round(
        distance_miles * IRS_MILEAGE_RATE,
        2
    )

    history = get_mileage()

    annual_miles_total = (
        calculate_annual_miles(history)
        + distance_miles
    )

    trip_record = {
        "trip_id": str(uuid.uuid4()),

        "date": datetime.utcnow().date().isoformat(),

        "start_time": trip["start_time"].isoformat(),
        "end_time": end_time.isoformat(),

        "duration_minutes": round(duration_minutes, 1),
        "distance_miles": distance_miles,
        "total_miles": distance_miles,

        "trip_type": "business",
        "status": "Completed",

        "destination": meta.get("destination"),
        "business_name": meta.get("business_name"),
        "client_name": meta.get("client_name"),
        "meeting_with": meta.get("meeting_with"),
        "purpose": meta.get("purpose"),
        "notes": meta.get("notes"),

        "start_location": meta.get("start_location"),
        "end_location": meta.get("end_location")
            or meta.get("destination"),

        "business_purpose": meta.get("purpose")
            or "Business",

        "odometer_start": meta.get("odometer_start"),
        "odometer_end": meta.get("odometer_end"),

        "irs_rate": IRS_MILEAGE_RATE,
        "deductible_amount": deductible_amount,

        "annual_miles_total": round(
            annual_miles_total,
            2
        ),

        "method": "standard_mileage",
        "created_by": "Max AI",

        # ==========================================
        # V1 RETURN-TRIP REMINDER
        # ==========================================

        "return_trip_required": True,
        "return_trip_logged": False,
        "reminder_dismissed": False,
        "parent_trip_id": None,

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


# =========================================================
# START TRACKING
# =========================================================

@router.post("/start")
async def start_mileage(
    meta: Dict = {},
    current_user=Depends(get_current_user)
):

    if not start_mileage_tracking(meta):

        return {
            "error": "Mileage already running"
        }

    return {
        "status": "Mileage tracking started"
    }


# =========================================================
# STOP TRACKING
# =========================================================

@router.post("/stop")
async def stop_mileage(
    current_user=Depends(get_current_user)
):

    result = stop_mileage_tracking()

    if not result:

        return {
            "error": "No active trip"
        }

    return result
# =========================================================
# ACTIVE TRIP STATUS
# =========================================================

@router.get("/active")
async def get_active_trip(
    current_user=Depends(get_current_user)
):
    trip = ACTIVE_TRIPS.get("current")

    if not trip:
        return {
            "active": False
        }

    meta = trip.get("meta", {})

    return {
        "active": True,
        "status": trip.get("status", "In Progress"),
        "start_time": trip["start_time"].isoformat(),
        "start_location": meta.get("start_location"),
        "destination": meta.get("destination"),
        "business_name": meta.get("business_name"),
        "client_name": meta.get("client_name"),
        "meeting_with": meta.get("meeting_with"),
        "purpose": meta.get("purpose") or "Business meeting"
    }

# =========================================================
# MANUAL TRIP
# =========================================================

@router.post("/manual")
async def create_manual_trip(
    data: ManualTripRequest,
    current_user=Depends(get_current_user)
):

    history = get_mileage()

    miles = round(float(data.miles), 2)

    deductible_amount = round(
        miles * IRS_MILEAGE_RATE,
        2
    )

    annual_total = (
        calculate_annual_miles(history)
        + miles
    )

    trip = {
        "trip_id": str(uuid.uuid4()),

        "date": data.date,

        "start_time": None,
        "end_time": None,
        "duration_minutes": 0,

        "start_location": data.start_location,
        "destination": data.destination,
        "end_location": data.destination,

        "purpose": data.purpose,
        "business_purpose": data.purpose,

        "business_name": None,
        "client_name": None,
        "meeting_with": None,
        "notes": None,

        "distance_miles": miles,
        "total_miles": miles,

        "trip_type": "business",
        "status": "Completed",

        "irs_rate": IRS_MILEAGE_RATE,

        "deductible_amount":
            deductible_amount,

        "annual_miles_total":
            round(annual_total, 2),

        "method": data.method or "manual",
        "created_by": "User",

        # RETURN REMINDER
        "return_trip_required": True,
        "return_trip_logged": False,
        "reminder_dismissed": False,
        "parent_trip_id": None,

        "audit_log": [
            {
                "action": "manual_trip_created",
                "by": "User",
                "date": datetime.utcnow().isoformat()
            }
        ]
    }

    history.append(trip)

    save_mileage(history)

    return {
        "success": True,
        "trip": trip
    }


# =========================================================
# GET HISTORY
# =========================================================

@router.get("/history")
async def get_trip_history(
    current_user=Depends(get_current_user)
):

    return get_mileage()


# =========================================================
# GET RETURN-TRIP REMINDERS
# =========================================================

@router.get("/reminders")
async def get_mileage_reminders(
    current_user=Depends(get_current_user)
):

    history = get_mileage()

    reminders = []

    for trip in history:

        if (
            trip.get("return_trip_required") is True
            and trip.get("return_trip_logged") is not True
            and trip.get("reminder_dismissed") is not True
            and not trip.get("parent_trip_id")
        ):

            reminders.append({
                "trip_id": trip.get("trip_id"),
                "date": trip.get("date"),
                "start_location":
                    trip.get("start_location"),
                "destination":
                    trip.get("destination")
                    or trip.get("end_location"),
                "purpose":
                    trip.get("business_purpose")
                    or trip.get("purpose"),
                "miles":
                    trip.get("total_miles")
                    or trip.get("distance_miles")
                    or 0
            })

    return {
        "success": True,
        "count": len(reminders),
        "reminders": reminders
    }


# =========================================================
# LOG RETURN TRIP
# =========================================================

@router.post("/return/{trip_id}")
async def log_return_trip(
    trip_id: str,
    current_user=Depends(get_current_user)
):

    history = get_mileage()

    original = next(
        (
            trip for trip in history
            if trip.get("trip_id") == trip_id
        ),
        None
    )

    if not original:

        raise HTTPException(
            status_code=404,
            detail="Original trip not found"
        )

    if original.get("return_trip_logged"):

        raise HTTPException(
            status_code=400,
            detail="Return trip already logged"
        )

    miles = float(
        original.get("total_miles")
        or original.get("distance_miles")
        or 0
    )

    deductible_amount = round(
        miles * IRS_MILEAGE_RATE,
        2
    )

    return_trip = {
        "trip_id": str(uuid.uuid4()),

        "date":
            datetime.utcnow().date().isoformat(),

        "start_time": None,
        "end_time": None,
        "duration_minutes": 0,

        # REVERSE LOCATIONS
        "start_location":
            original.get("destination")
            or original.get("end_location"),

        "destination":
            original.get("start_location"),

        "end_location":
            original.get("start_location"),

        "purpose":
            original.get("purpose")
            or original.get("business_purpose")
            or "Business return trip",

        "business_purpose":
            original.get("business_purpose")
            or original.get("purpose")
            or "Business return trip",

        "business_name":
            original.get("business_name"),

        "client_name":
            original.get("client_name"),

        "meeting_with":
            original.get("meeting_with"),

        "notes":
            "Return trip",

        "distance_miles": miles,
        "total_miles": miles,

        "trip_type": "business",
        "status": "Completed",

        "irs_rate": IRS_MILEAGE_RATE,

        "deductible_amount":
            deductible_amount,

        "annual_miles_total":
            round(
                calculate_annual_miles(history)
                + miles,
                2
            ),

        "method": "return_trip",
        "created_by": "User",

        # Prevent another reminder from being
        # generated for the return journey
        "return_trip_required": False,
        "return_trip_logged": True,
        "reminder_dismissed": False,

        "parent_trip_id": trip_id,

        "audit_log": [
            {
                "action": "return_trip_logged",
                "by": "User",
                "date": datetime.utcnow().isoformat()
            }
        ]
    }

    original["return_trip_logged"] = True

    original.setdefault(
        "audit_log",
        []
    ).append({
        "action": "return_trip_confirmed",
        "by": "User",
        "date": datetime.utcnow().isoformat()
    })

    history.append(return_trip)

    save_mileage(history)

    return {
        "success": True,
        "message": "Return trip logged",
        "trip": return_trip
    }


# =========================================================
# DISMISS REMINDER
# =========================================================

@router.put("/reminders/{trip_id}/dismiss")
async def dismiss_mileage_reminder(
    trip_id: str,
    current_user=Depends(get_current_user)
):

    history = get_mileage()

    found = False

    for trip in history:

        if trip.get("trip_id") == trip_id:

            trip["reminder_dismissed"] = True

            trip.setdefault(
                "audit_log",
                []
            ).append({
                "action": "return_reminder_dismissed",
                "by": "User",
                "date": datetime.utcnow().isoformat()
            })

            found = True
            break

    if not found:

        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    save_mileage(history)

    return {
        "success": True
    }


# =========================================================
# DELETE TRIP
# =========================================================

@router.delete("/{trip_id}")
async def delete_mileage_trip(
    trip_id: str,
    current_user=Depends(get_current_user)
):

    history = get_mileage()

    new_history = [
        trip for trip in history
        if trip.get("trip_id") != trip_id
    ]

    if len(new_history) == len(history):

        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    save_mileage(new_history)

    return {
        "success": True
    }