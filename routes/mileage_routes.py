from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import uuid
import math
from typing import Optional, Dict, Any

from pydantic import BaseModel

from dependencies.auth_dependency import get_current_user
from models.storage import get_mileage, save_mileage


router = APIRouter(
    prefix="/mileage",
    tags=["Mileage"],
)


# =========================================================
# CONFIGURATION
# =========================================================

# 2026 IRS business mileage rate.
#
# Keep this value centralized so it can be updated easily
# if your tax logic later uses a different rate.
IRS_MILEAGE_RATE = 0.76

# Ignore tiny GPS movements caused by GPS noise.
MIN_GPS_MOVEMENT_METERS = 10.0

# Reject obviously impossible GPS jumps.
MAX_REASONABLE_SPEED_MPH = 120.0


# =========================================================
# ACTIVE TRIPS
# =========================================================
#
# Each authenticated user gets their own active trip.
#
# OLD:
#     ACTIVE_TRIPS["current"]
#
# NEW:
#     ACTIVE_TRIPS[user_id]
#
# This prevents one user's trip from affecting another user's
# trip.
#
# NOTE:
# This is still in-memory.
#
# If the FastAPI process restarts, active trips disappear.
# Persistent active-trip storage should be added later.
#

ACTIVE_TRIPS: Dict[str, Dict[str, Any]] = {}


# =========================================================
# MODELS
# =========================================================


class GPSLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None


class ManualTripRequest(BaseModel):
    date: str
    start_location: str
    destination: str
    purpose: Optional[str] = "Business"
    miles: float
    method: Optional[str] = "manual"


class EditMileageRequest(BaseModel):
    miles: float


class GPSUpdateRequest(BaseModel):
    location: GPSLocation


# =========================================================
# HELPERS
# =========================================================


def validate_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    """
    Validate latitude and longitude values.
    """

    if not math.isfinite(latitude):
        raise ValueError("Latitude must be a finite number")

    if not math.isfinite(longitude):
        raise ValueError("Longitude must be a finite number")

    if not -90 <= latitude <= 90:
        raise ValueError("Invalid latitude")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid longitude")


def calculate_annual_miles(
    history,
    user_id: Optional[str] = None,
) -> float:
    """
    Calculate total mileage for the current UTC calendar year.

    When user_id is supplied, include only records explicitly
    owned by that user.
    """

    total = 0.0
    current_year = datetime.now(timezone.utc).year
    user_id = str(user_id) if user_id is not None else None

    for trip in history:
        if user_id is not None and str(trip.get("user_id", "")) != user_id:
            continue

        trip_date = str(trip.get("date", ""))

        if trip_date.startswith(str(current_year)):
            try:
                total += float(trip.get("total_miles", 0) or 0)
            except (TypeError, ValueError):
                continue

    return round(total, 2)


# =========================================================
# HAVERSINE DISTANCE
# =========================================================


def calculate_distance_miles(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate straight-line distance between two GPS points.

    Returns miles.
    """

    validate_coordinates(
        lat1,
        lon1,
    )

    validate_coordinates(
        lat2,
        lon2,
    )

    earth_radius_meters = 6_371_000.0

    lat1_rad = math.radians(
        lat1
    )

    lat2_rad = math.radians(
        lat2
    )

    delta_lat = math.radians(
        lat2 - lat1
    )

    delta_lon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(
            delta_lat / 2
        ) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(
            delta_lon / 2
        ) ** 2
    )

    # Protect against floating-point rounding.
    a = max(
        0.0,
        min(
            1.0,
            a,
        ),
    )

    c = (
        2
        *
        math.atan2(
            math.sqrt(a),
            math.sqrt(
                1 - a
            ),
        )
    )

    meters = (
        earth_radius_meters
        * c
    )

    miles = (
        meters
        / 1609.344
    )

    return miles


# =========================================================
# GET USER ACTIVE TRIP
# =========================================================


def get_user_active_trip(
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get the currently active trip for one user.
    """

    return ACTIVE_TRIPS.get(
        str(user_id)
    )


# =========================================================
# START MILEAGE TRACKING
# =========================================================


def start_mileage_tracking(
    user_id: str,
    trip_meta: Optional[Dict] = None,
) -> bool:
    """
    Start a GPS mileage trip for a specific user.

    Returns:
        True  -> trip started
        False -> trip could not be started
    """

    user_id = str(
        user_id
    )

    # -----------------------------------------------------
    # PREVENT DUPLICATE ACTIVE TRIP
    # -----------------------------------------------------

    existing = ACTIVE_TRIPS.get(
        user_id
    )

    if existing:

        print(
            "MILEAGE START REJECTED: "
            f"Trip already active for user {user_id}"
        )

        return False

    trip_meta = (
        dict(trip_meta)
        if isinstance(
            trip_meta,
            dict,
        )
        else {}
    )

    # -----------------------------------------------------
    # GPS START LOCATION
    # -----------------------------------------------------

    start_location = trip_meta.get(
        "start_location"
    )

    if not isinstance(
        start_location,
        dict,
    ):

        print(
            "MILEAGE START ERROR: "
            "No valid start GPS received"
        )

        return False

    latitude = start_location.get(
        "latitude"
    )

    longitude = start_location.get(
        "longitude"
    )

    accuracy = start_location.get(
        "accuracy"
    )

    if (
        latitude is None
        or longitude is None
    ):

        print(
            "MILEAGE START ERROR: "
            "GPS coordinates missing"
        )

        return False

    try:

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

        if accuracy is not None:

            accuracy = float(
                accuracy
            )

        validate_coordinates(
            latitude,
            longitude,
        )

    except (
        TypeError,
        ValueError,
    ) as e:

        print(
            "MILEAGE START GPS ERROR: "
            f"{e}"
        )

        return False

    # -----------------------------------------------------
    # START TIME
    # -----------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    # -----------------------------------------------------
    # CREATE ACTIVE TRIP
    # -----------------------------------------------------

    ACTIVE_TRIPS[user_id] = {

        "user_id":
            user_id,

        "trip_id":
            str(
                uuid.uuid4()
            ),

        "start_time":
            now,

        "last_gps_time":
            now,

        "status":
            "In Progress",

        "created_by":
            "Max AI",

        "meta":
            trip_meta,

        # -------------------------------------------------
        # GPS TRACK
        # -------------------------------------------------

        "gps_points": [

            {
                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "accuracy":
                    accuracy,

                "timestamp":
                    now.isoformat(),
            }

        ],

        "gps_distance_miles":
            0.0,
    }

    print(
        "========== MILEAGE STARTED =========="
    )

    print(
        f"USER ID: {user_id}"
    )

    print(
        "TRIP ID: "
        f"{ACTIVE_TRIPS[user_id]['trip_id']}"
    )

    print(
        f"START LATITUDE: {latitude}"
    )

    print(
        f"START LONGITUDE: {longitude}"
    )

    print(
        f"START ACCURACY: {accuracy}"
    )

    print(
        "======================================"
    )

    return True


# =========================================================
# UPDATE MILEAGE GPS
# =========================================================


def update_mileage_location(
    user_id: str,
    location: Dict,
) -> Dict[str, Any]:
    """
    Add a new GPS point to the active trip.

    Distance is calculated from the previous accepted
    GPS point.
    """

    user_id = str(
        user_id
    )

    trip = ACTIVE_TRIPS.get(
        user_id
    )

    if not trip:

        return {
            "success": False,
            "error": "No active trip",
        }

    if not isinstance(
        location,
        dict,
    ):

        return {
            "success": False,
            "error": "Invalid GPS location",
        }

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    accuracy = location.get(
        "accuracy"
    )

    if (
        latitude is None
        or longitude is None
    ):

        return {
            "success": False,
            "error":
                "GPS coordinates are required",
        }

    try:

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

        if accuracy is not None:

            accuracy = float(
                accuracy
            )

        validate_coordinates(
            latitude,
            longitude,
        )

    except (
        TypeError,
        ValueError,
    ) as e:

        return {
            "success": False,
            "error":
                f"Invalid GPS coordinates: {e}",
        }

    now = datetime.now(
        timezone.utc
    )

    gps_points = trip.get(
        "gps_points",
        [],
    )

    # -----------------------------------------------------
    # FIRST GPS POINT
    # -----------------------------------------------------

    if not gps_points:

        gps_points.append({

            "latitude":
                latitude,

            "longitude":
                longitude,

            "accuracy":
                accuracy,

            "timestamp":
                now.isoformat(),
        })

        trip[
            "gps_points"
        ] = gps_points

        trip[
            "last_gps_time"
        ] = now

        return {

            "success":
                True,

            "accepted":
                True,

            "added_miles":
                0.0,

            "total_miles":
                0.0,
        }

    # -----------------------------------------------------
    # LAST ACCEPTED GPS POINT
    # -----------------------------------------------------

    last_point = gps_points[-1]

    try:

        last_latitude = float(
            last_point[
                "latitude"
            ]
        )

        last_longitude = float(
            last_point[
                "longitude"
            ]
        )

    except (
        TypeError,
        ValueError,
        KeyError,
    ):

        return {
            "success": False,
            "error":
                "Stored GPS point is invalid",
        }

    distance = calculate_distance_miles(

        last_latitude,

        last_longitude,

        latitude,

        longitude,
    )

    # -----------------------------------------------------
    # ELAPSED TIME
    # -----------------------------------------------------

    last_gps_time = trip.get(
        "last_gps_time"
    )

    if not isinstance(
        last_gps_time,
        datetime,
    ):

        last_gps_time = now

    elapsed_seconds = (
        now
        -
        last_gps_time
    ).total_seconds()

    # Prevent negative elapsed time.
    elapsed_seconds = max(
        elapsed_seconds,
        0.0,
    )

    # -----------------------------------------------------
    # GPS NOISE FILTER
    # -----------------------------------------------------

    distance_meters = (
        distance
        * 1609.344
    )

    if (
        distance_meters
        <
        MIN_GPS_MOVEMENT_METERS
    ):

        # Update time even when movement is ignored.
        trip[
            "last_gps_time"
        ] = now

        return {

            "success":
                True,

            "accepted":
                False,

            "reason":
                "GPS movement too small",

            "added_miles":
                0.0,

            "total_miles":
                round(
                    trip.get(
                        "gps_distance_miles",
                        0.0,
                    ),
                    2,
                ),
        }

    # -----------------------------------------------------
    # IMPOSSIBLE SPEED FILTER
    # -----------------------------------------------------

    if elapsed_seconds > 0:

        speed_mph = (

            distance
            /
            (
                elapsed_seconds
                /
                3600.0
            )
        )

        if (
            speed_mph
            >
            MAX_REASONABLE_SPEED_MPH
        ):

            print(
                "GPS POINT REJECTED: "
                f"Impossible speed "
                f"{speed_mph:.1f} MPH"
            )

            # IMPORTANT:
            # Do NOT update last_gps_time here.
            #
            # This prevents a rejected GPS jump from
            # becoming the new baseline point.

            return {

                "success":
                    True,

                "accepted":
                    False,

                "reason":
                    "GPS jump rejected",

                "speed_mph":
                    round(
                        speed_mph,
                        1,
                    ),

                "total_miles":
                    round(
                        trip.get(
                            "gps_distance_miles",
                            0.0,
                        ),
                        2,
                    ),
            }

    # -----------------------------------------------------
    # ACCEPT GPS POINT
    # -----------------------------------------------------

    current_distance = float(
        trip.get(
            "gps_distance_miles",
            0.0,
        )
        or 0.0
    )

    current_distance += distance

    trip[
        "gps_distance_miles"
    ] = current_distance

    trip[
        "last_gps_time"
    ] = now

    gps_points.append({

        "latitude":
            latitude,

        "longitude":
            longitude,

        "accuracy":
            accuracy,

        "timestamp":
            now.isoformat(),
    })

    # -----------------------------------------------------
    # PREVENT UNLIMITED MEMORY GROWTH
    # -----------------------------------------------------
    #
    # For the current proof of concept we retain the GPS
    # points in the active trip. Later this can be moved to
    # a persistent GPS tracking table.
    #

    max_points = 5000

    if len(gps_points) > max_points:

        del gps_points[
            :len(gps_points) - max_points
        ]

    print(
        "GPS POINT ACCEPTED: "
        f"+{distance:.3f} miles "
        f"| TOTAL: "
        f"{current_distance:.3f}"
    )

    return {

        "success":
            True,

        "accepted":
            True,

        "added_miles":
            round(
                distance,
                3,
            ),

        "total_miles":
            round(
                current_distance,
                2,
            ),
    }


# =========================================================
# STOP MILEAGE TRACKING
# =========================================================


def stop_mileage_tracking(
    user_id: str,
    end_location: Optional[Dict] = None,
):
    """
    Stop the user's active trip.

    IMPORTANT:
    This function no longer creates fake mileage from
    duration.

    Mileage comes only from accepted GPS points.
    """

    user_id = str(
        user_id
    )

    trip = ACTIVE_TRIPS.get(
        user_id
    )

    if not trip:

        return None

    # -----------------------------------------------------
    # ADD FINAL GPS POSITION
    # -----------------------------------------------------

    if end_location:

        final_result = (
            update_mileage_location(
                user_id=user_id,
                location=end_location,
            )
        )

        if not final_result.get(
            "success"
        ):

            print(
                "FINAL GPS UPDATE FAILED:"
            )

            print(
                final_result
            )

    end_time = datetime.now(
        timezone.utc
    )

    duration_minutes = (
        end_time
        -
        trip[
            "start_time"
        ]
    ).total_seconds() / 60.0

    # -----------------------------------------------------
    # REAL GPS DISTANCE
    # -----------------------------------------------------

    distance_miles = round(

        float(
            trip.get(
                "gps_distance_miles",
                0.0,
            )
            or 0.0
        ),

        2,
    )

    # -----------------------------------------------------
    # DO NOT CREATE FAKE MILEAGE
    # -----------------------------------------------------

    if distance_miles <= 0:

        print(
            "MILEAGE STOP WARNING: "
            "No GPS mileage recorded"
        )

        # Keep the trip active.
        #
        # This allows the user to continue tracking
        # instead of accidentally losing the trip.

        return {

            "error":
                "No GPS mileage was recorded. "
                "Please continue the trip until "
                "GPS movement is detected."
        }

    # -----------------------------------------------------
    # TRIP META
    # -----------------------------------------------------

    meta = trip.get(
        "meta",
        {},
    )

    if not isinstance(
        meta,
        dict,
    ):

        meta = {}

    # -----------------------------------------------------
    # TAX DEDUCTION
    # -----------------------------------------------------

    deductible_amount = round(

        distance_miles
        *
        IRS_MILEAGE_RATE,

        2,
    )

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    annual_miles_total = (

        calculate_annual_miles(
            history,
            user_id=user_id,
        )
        +
        distance_miles
    )

    # -----------------------------------------------------
    # START LOCATION
    # -----------------------------------------------------

    start_location = (
        meta.get(
            "start_location"
        )
    )

    # -----------------------------------------------------
    # END LOCATION
    # -----------------------------------------------------

    final_location = end_location

    if not final_location:

        gps_points = trip.get(
            "gps_points",
            [],
        )

        if gps_points:

            last_point = gps_points[-1]

            final_location = {

                "latitude":
                    last_point.get(
                        "latitude"
                    ),

                "longitude":
                    last_point.get(
                        "longitude"
                    ),

                "accuracy":
                    last_point.get(
                        "accuracy"
                    ),
            }

    # -----------------------------------------------------
    # TRIP RECORD
    # -----------------------------------------------------

    trip_record = {

        "trip_id":
            trip[
                "trip_id"
            ],

        "user_id":
            user_id,

        "date":
            end_time.date().isoformat(),

        "start_time":
            trip[
                "start_time"
            ].isoformat(),

        "end_time":
            end_time.isoformat(),

        "duration_minutes":
            round(
                duration_minutes,
                1,
            ),

        "distance_miles":
            distance_miles,

        "total_miles":
            distance_miles,

        "trip_type":
            "business",

        "status":
            "Completed",

        "destination":
            meta.get(
                "destination"
            ),

        "business_name":
            meta.get(
                "business_name"
            ),

        "client_name":
            meta.get(
                "client_name"
            ),

        "meeting_with":
            meta.get(
                "meeting_with"
            ),

        "purpose":
            meta.get(
                "purpose"
            ),

        "notes":
            meta.get(
                "notes"
            ),

        "start_location":
            start_location,

        "end_location":
            final_location,

        "business_purpose":
            meta.get(
                "purpose"
            )
            or
            "Business",

        "odometer_start":
            meta.get(
                "odometer_start"
            ),

        "odometer_end":
            meta.get(
                "odometer_end"
            ),

        "irs_rate":
            IRS_MILEAGE_RATE,

        "deductible_amount":
            deductible_amount,

        "annual_miles_total":
            round(
                annual_miles_total,
                2,
            ),

        "method":
            "gps_tracking",

        "created_by":
            "Max AI",

        # -------------------------------------------------
        # RETURN TRIP
        # -------------------------------------------------

        "return_trip_required":
            True,

        "return_trip_logged":
            False,

        "reminder_dismissed":
            False,

        "parent_trip_id":
            None,

        # -------------------------------------------------
        # GPS AUDIT DATA
        # -------------------------------------------------

        "gps_points":
            trip.get(
                "gps_points",
                [],
            ),

        # -------------------------------------------------
        # AUDIT
        # -------------------------------------------------

        "audit_log": [

            {

                "action":
                    "trip_completed",

                "by":
                    "Max AI",

                "date":
                    end_time.isoformat(),
            }

        ],
    }

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    history.append(
        trip_record
    )

    print(
        "========== SAVING MILEAGE =========="
    )

    print(
        f"USER ID: {user_id}"
    )

    print(
        "TRIP ID: "
        f"{trip['trip_id']}"
    )

    print(
        f"DISTANCE: "
        f"{distance_miles} miles"
    )

    print(
        f"RATE: "
        f"${IRS_MILEAGE_RATE}"
    )

    print(
        f"DEDUCTION: "
        f"${deductible_amount}"
    )

    print(
        "===================================="
    )

    save_mileage(
        history
    )

    # -----------------------------------------------------
    # REMOVE ONLY THIS USER'S ACTIVE TRIP
    # -----------------------------------------------------

    ACTIVE_TRIPS.pop(
        user_id,
        None,
    )

    print(
        "========== SAVE COMPLETE =========="
    )

    return trip_record


# =========================================================
# START API
# =========================================================


@router.post("/start")
async def start_mileage(
    meta: Dict = {},
    current_user=Depends(
        get_current_user
    ),
):

    user_id = str(
        current_user.id
    )

    started = start_mileage_tracking(

        user_id=user_id,

        trip_meta=meta,
    )

    if not started:

        return {

            "success":
                False,

            "error":
                "Mileage is already running "
                "or a valid GPS start location "
                "was not provided.",
        }

    return {

        "success":
            True,

        "status":
            "Mileage tracking started",
    }


# =========================================================
# GPS LOCATION API
# =========================================================


@router.post("/location")
async def update_location(
    data: GPSUpdateRequest,
    current_user=Depends(
        get_current_user
    ),
):

    user_id = str(
        current_user.id
    )

    result = update_mileage_location(

        user_id=user_id,

        location=data.location.model_dump(),
    )

    if not result.get(
        "success"
    ):

        raise HTTPException(

            status_code=400,

            detail=result.get(
                "error",
                "Unable to update GPS",
            ),
        )

    return result


# =========================================================
# STOP API
# =========================================================


@router.post("/stop")
async def stop_mileage(
    end_location: Optional[GPSLocation] = None,
    current_user=Depends(
        get_current_user
    ),
):

    user_id = str(
        current_user.id
    )

    result = stop_mileage_tracking(

        user_id=user_id,

        end_location=(

            end_location.model_dump()

            if end_location

            else None
        ),
    )

    # -----------------------------------------------------
    # NO ACTIVE TRIP
    # -----------------------------------------------------

    if not result:

        return {

            "success":
                False,

            "error":
                "No active trip",
        }

    # -----------------------------------------------------
    # MILEAGE ERROR
    # -----------------------------------------------------

    if result.get(
        "error"
    ):

        return {

            "success":
                False,

            "error":
                result[
                    "error"
                ],
        }

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    return {

        "success":
            True,

        "trip":
            result,
    }


# =========================================================
# ACTIVE TRIP
# =========================================================


@router.get("/active")
async def get_active_trip(
    current_user=Depends(
        get_current_user
    ),
):

    user_id = str(
        current_user.id
    )

    trip = get_user_active_trip(
        user_id
    )

    if not trip:

        return {
            "active":
                False
        }

    meta = trip.get(
        "meta",
        {},
    )

    if not isinstance(
        meta,
        dict,
    ):

        meta = {}

    return {

        "active":
            True,

        "trip_id":
            trip.get(
                "trip_id"
            ),

        "status":
            trip.get(
                "status",
                "In Progress",
            ),

        "start_time":
            trip[
                "start_time"
            ].isoformat(),

        "start_location":
            meta.get(
                "start_location"
            ),

        "destination":
            meta.get(
                "destination"
            ),

        "business_name":
            meta.get(
                "business_name"
            ),

        "client_name":
            meta.get(
                "client_name"
            ),

        "meeting_with":
            meta.get(
                "meeting_with"
            ),

        "purpose":
            meta.get(
                "purpose"
            )
            or
            "Business meeting",

        "current_miles":
            round(
                float(
                    trip.get(
                        "gps_distance_miles",
                        0,
                    )
                    or 0
                ),
                2,
            ),
    }


# =========================================================
# MANUAL TRIP
# =========================================================


@router.post("/manual")
async def create_manual_trip(
    data: ManualTripRequest,
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    try:

        miles = round(
            float(
                data.miles
            ),
            2,
        )

    except (
        TypeError,
        ValueError,
    ):

        raise HTTPException(

            status_code=400,

            detail="Miles must be a valid number",
        )

    if not math.isfinite(
        miles
    ):

        raise HTTPException(

            status_code=400,

            detail="Miles must be a finite number",
        )

    if miles < 0:

        raise HTTPException(

            status_code=400,

            detail="Miles cannot be negative",
        )

    deductible_amount = round(

        miles
        *
        IRS_MILEAGE_RATE,

        2,
    )

    annual_total = (

        calculate_annual_miles(
            history,
            user_id=str(current_user.id),
        )
        +
        miles
    )

    trip = {

        "trip_id":
            str(
                uuid.uuid4()
            ),

        "user_id":
            str(
                current_user.id
            ),

        "date":
            data.date,

        "start_time":
            None,

        "end_time":
            None,

        "duration_minutes":
            0,

        "start_location":
            data.start_location,

        "destination":
            data.destination,

        "end_location":
            data.destination,

        "purpose":
            data.purpose,

        "business_purpose":
            data.purpose,

        "business_name":
            None,

        "client_name":
            None,

        "meeting_with":
            None,

        "notes":
            None,

        "distance_miles":
            miles,

        "total_miles":
            miles,

        "trip_type":
            "business",

        "status":
            "Completed",

        "irs_rate":
            IRS_MILEAGE_RATE,

        "deductible_amount":
            deductible_amount,

        "annual_miles_total":
            round(
                annual_total,
                2,
            ),

        "method":
            data.method
            or
            "manual",

        "created_by":
            "User",

        # -------------------------------------------------
        # RETURN REMINDER
        # -------------------------------------------------

        "return_trip_required":
            True,

        "return_trip_logged":
            False,

        "reminder_dismissed":
            False,

        "parent_trip_id":
            None,

        # -------------------------------------------------
        # AUDIT
        # -------------------------------------------------

        "audit_log": [

            {

                "action":
                    "manual_trip_created",

                "by":
                    "User",

                "date":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }

        ],
    }

    history.append(
        trip
    )

    save_mileage(
        history
    )

    return {

        "success":
            True,

        "trip":
            trip,
    }


# =========================================================
# HISTORY
# =========================================================


@router.get("/history")
async def get_trip_history(
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(history, list):
        return []

    current_user_id = str(current_user.id)

    return [
        trip
        for trip in history
        if str(trip.get("user_id", "")) == current_user_id
    ]


# =========================================================
# REMINDERS
# =========================================================


@router.get("/reminders")
async def get_mileage_reminders(
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    current_user_id = str(current_user.id)
    reminders = []
    seen_trip_ids = set()

    for trip in history:
        # Never expose reminders for records not explicitly owned
        # by the authenticated user.
        if str(trip.get("user_id", "")) != current_user_id:
            continue

        trip_id = trip.get("trip_id")

        if not trip_id or trip_id in seen_trip_ids:
            continue

        if (
            trip.get("return_trip_required") is True
            and trip.get("return_trip_logged") is not True
            and trip.get("reminder_dismissed") is not True
            and not trip.get("parent_trip_id")
        ):
            seen_trip_ids.add(trip_id)
            reminders.append({
                "trip_id": trip_id,
                "date": trip.get("date"),
                "start_location": trip.get("start_location"),
                "destination": (
                    trip.get("destination")
                    or trip.get("end_location")
                ),
                "purpose": (
                    trip.get("business_purpose")
                    or trip.get("purpose")
                ),
                "miles": (
                    trip.get("total_miles")
                    or trip.get("distance_miles")
                    or 0
                ),
            })

    return {
        "success": True,
        "count": len(reminders),
        "reminders": reminders,
    }


# =========================================================
# RETURN TRIP
# =========================================================


@router.post(
    "/return/{trip_id}"
)
async def log_return_trip(
    trip_id: str,
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    current_user_id = str(
        current_user.id
    )

    # -----------------------------------------------------
    # FIND ORIGINAL TRIP
    # -----------------------------------------------------

    original = next(

        (

            trip

            for trip in history

            if (

                trip.get(
                    "trip_id"
                )
                ==
                trip_id

                and

                str(trip.get("user_id", ""))
                ==
                current_user_id
            )

        ),

        None,
    )

    if not original:

        raise HTTPException(

            status_code=404,

            detail="Original trip not found",
        )

    # -----------------------------------------------------
    # CHECK DUPLICATE
    # -----------------------------------------------------

    if original.get(
        "return_trip_logged"
    ):

        raise HTTPException(

            status_code=400,

            detail="Return trip already logged",
        )

    # -----------------------------------------------------
    # ORIGINAL MILEAGE
    # -----------------------------------------------------

    try:

        miles = float(

            original.get(
                "total_miles"
            )
            or
            original.get(
                "distance_miles"
            )
            or
            0
        )

    except (
        TypeError,
        ValueError,
    ):

        miles = 0.0

    if miles <= 0:

        raise HTTPException(

            status_code=400,

            detail="Original trip has no valid mileage",
        )

    deductible_amount = round(

        miles
        *
        IRS_MILEAGE_RATE,

        2,
    )

    # -----------------------------------------------------
    # CREATE RETURN TRIP
    # -----------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    return_trip = {

        "trip_id":
            str(
                uuid.uuid4()
            ),

        "user_id":
            current_user_id,

        "date":
            now.date().isoformat(),

        "start_time":
            None,

        "end_time":
            None,

        "duration_minutes":
            0,

        # -------------------------------------------------
        # REVERSE LOCATIONS
        # -------------------------------------------------

        "start_location":
            original.get(
                "destination"
            )
            or
            original.get(
                "end_location"
            ),

        "destination":
            original.get(
                "start_location"
            ),

        "end_location":
            original.get(
                "start_location"
            ),

        # -------------------------------------------------
        # BUSINESS DETAILS
        # -------------------------------------------------

        "purpose":
            original.get(
                "purpose"
            )
            or
            original.get(
                "business_purpose"
            )
            or
            "Business return trip",

        "business_purpose":
            original.get(
                "business_purpose"
            )
            or
            original.get(
                "purpose"
            )
            or
            "Business return trip",

        "business_name":
            original.get(
                "business_name"
            ),

        "client_name":
            original.get(
                "client_name"
            ),

        "meeting_with":
            original.get(
                "meeting_with"
            ),

        "notes":
            "Return trip",

        # -------------------------------------------------
        # MILEAGE
        # -------------------------------------------------

        "distance_miles":
            miles,

        "total_miles":
            miles,

        "trip_type":
            "business",

        "status":
            "Completed",

        "irs_rate":
            IRS_MILEAGE_RATE,

        "deductible_amount":
            deductible_amount,

        "annual_miles_total":
            round(

                calculate_annual_miles(
                    history,
                    user_id=current_user_id,
                )
                +
                miles,

                2,
            ),

        "method":
            "return_trip",

        "created_by":
            "User",

        # -------------------------------------------------
        # NO SECOND RETURN REMINDER
        # -------------------------------------------------

        "return_trip_required":
            False,

        "return_trip_logged":
            True,

        "reminder_dismissed":
            False,

        "parent_trip_id":
            trip_id,

        # -------------------------------------------------
        # AUDIT
        # -------------------------------------------------

        "audit_log": [

            {

                "action":
                    "return_trip_logged",

                "by":
                    "User",

                "date":
                    now.isoformat(),
            }

        ],
    }

    # -----------------------------------------------------
    # MARK ORIGINAL COMPLETE
    # -----------------------------------------------------

    original[
        "return_trip_logged"
    ] = True

    original.setdefault(
        "audit_log",
        []
    ).append({

        "action":
            "return_trip_confirmed",

        "by":
            "User",

        "date":
            now.isoformat(),
    })

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    history.append(
        return_trip
    )

    save_mileage(
        history
    )

    return {

        "success":
            True,

        "message":
            "Return trip logged",

        "trip":
            return_trip,
    }


# =========================================================
# DISMISS REMINDER
# =========================================================


@router.put(
    "/reminders/{trip_id}/dismiss"
)
async def dismiss_mileage_reminder(
    trip_id: str,
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    current_user_id = str(
        current_user.id
    )

    found = False

    for trip in history:

        if (

            trip.get(
                "trip_id"
            )
            ==
            trip_id

            and

            str(trip.get("user_id", ""))
            ==
            current_user_id

        ):

            trip[
                "reminder_dismissed"
            ] = True

            trip.setdefault(
                "audit_log",
                []
            ).append({

                "action":
                    "return_reminder_dismissed",

                "by":
                    "User",

                "date":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            })

            found = True

            break

    if not found:

        raise HTTPException(

            status_code=404,

            detail="Trip not found",
        )

    save_mileage(
        history
    )

    return {

        "success":
            True
    }


# =========================================================
# EDIT MILEAGE
# =========================================================


@router.put(
    "/edit/{trip_id}"
)
async def edit_mileage(
    trip_id: str,
    data: EditMileageRequest,
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    current_user_id = str(
        current_user.id
    )

    for trip in history:

        if (

            trip.get(
                "trip_id"
            )
            ==
            trip_id

            and

            str(trip.get("user_id", ""))
            ==
            current_user_id

        ):

            try:

                miles = round(

                    float(
                        data.miles
                    ),

                    2,
                )

            except (
                TypeError,
                ValueError,
            ):

                raise HTTPException(

                    status_code=400,

                    detail=
                        "Miles must be a valid number",
                )

            if not math.isfinite(
                miles
            ):

                raise HTTPException(

                    status_code=400,

                    detail=
                        "Miles must be a finite number",
                )

            if miles < 0:

                raise HTTPException(

                    status_code=400,

                    detail=
                        "Miles cannot be negative",
                )

            trip[
                "total_miles"
            ] = miles

            trip[
                "distance_miles"
            ] = miles

            trip[
                "deductible_amount"
            ] = round(

                miles
                *
                IRS_MILEAGE_RATE,

                2,
            )

            trip[
                "manually_edited"
            ] = True

            trip.setdefault(
                "audit_log",
                []
            ).append({

                "action":
                    "mileage_edited",

                "by":
                    "User",

                "date":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            })

            save_mileage(
                history
            )

            return {

                "success":
                    True,

                "trip":
                    trip,
            }

    raise HTTPException(

        status_code=404,

        detail="Trip not found",
    )


# =========================================================
# DELETE TRIP
# =========================================================


@router.delete(
    "/{trip_id}"
)
async def delete_mileage_trip(
    trip_id: str,
    current_user=Depends(
        get_current_user
    ),
):

    history = get_mileage()

    if not isinstance(
        history,
        list,
    ):

        history = []

    current_user_id = str(
        current_user.id
    )

    # -----------------------------------------------------
    # CHECK THAT THE TRIP BELONGS TO USER
    # -----------------------------------------------------

    found = False

    for trip in history:

        if (

            trip.get(
                "trip_id"
            )
            ==
            trip_id

            and

            str(trip.get("user_id", ""))
            ==
            current_user_id

        ):

            found = True
            break

    if not found:

        raise HTTPException(

            status_code=404,

            detail="Trip not found",
        )

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    new_history = [

        trip

        for trip in history

        if not (

            trip.get(
                "trip_id"
            )
            ==
            trip_id

            and

            str(trip.get("user_id", ""))
            ==
            current_user_id
        )
    ]

    save_mileage(
        new_history
    )

    return {

        "success":
            True
    }