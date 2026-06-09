from fastapi import APIRouter, UploadFile, File, Body
import uuid
from datetime import datetime
import os
import shutil

from services.aiAnalyzer import analyze_receipt_image
from services.irs_rules import apply_irs_rules

from models.storage import (
    get_receipts,
    save_receipts,
    save_vendor_correction
)

from services.currency_service import convert_to_usd
from routes.xero_routes import xero_create_bill

router = APIRouter(prefix="/receipts", tags=["Receipts"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):

    file_extension = os.path.splitext(file.filename)[1]

    unique_filename = (
        f"{uuid.uuid4()}{file_extension}"
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(file_path, "rb") as f:
        contents = f.read()

    analyzed_data = await analyze_receipt_image(
        contents
    )

    # ✅ CURRENCY CONVERSION
    converted_amount = convert_to_usd(
        analyzed_data.get("amount"),
        analyzed_data.get("currency")
    )

    irs_data = apply_irs_rules(
        analyzed_data.get("category"),
        converted_amount
    )

    receipt_record = {

        "id": str(uuid.uuid4()),

        "filename": unique_filename,

        "uploaded_at":
            datetime.utcnow().isoformat(),

        "vendor":
            analyzed_data.get("vendor"),

        "date":
            analyzed_data.get("date"),

        "amount":
            analyzed_data.get("amount"),

        "currency":
            analyzed_data.get(
                "currency",
                "USD"
            ),

        "usd_amount":
            converted_amount,

        "category":
            analyzed_data.get("category"),

        "document_type":
            analyzed_data.get(
                "document_type"
            ),

        "deduction_type":
            analyzed_data.get(
                "deduction_type"
            ),

        "vendor_learned":
            analyzed_data.get(
                "vendor_learned",
                False
            ),

        "status": (
            "Needs Review"
            if analyzed_data.get(
                "needs_review"
            )
            else "Pending"
        ),

        "source": "upload",

        "ai_extracted": True,

        "ai_confidence":
            analyzed_data.get(
                "ai_confidence",
                "low"
            ),

        "needs_review":
            analyzed_data.get(
                "needs_review",
                False
            ),

        "is_blurry":
            analyzed_data.get(
                "is_blurry",
                False
            ),

        "blur_score":
            analyzed_data.get(
                "blur_score",
                0
            ),

        "is_dark":
            analyzed_data.get(
                "is_dark",
                False
            ),

        "manually_edited": False,

        "irs_category":
            irs_data["irs_category"],

        "deductible_percent":
            irs_data[
                "deductible_percent"
            ],

        "deductible_amount":
            irs_data[
                "deductible_amount"
            ],

        "rule_applied":
            irs_data["rule_applied"],

        "xero_synced": False,

"possible_duplicate": False,

"duplicate_of": None,

"audit_log": [

            {
                "action": "created",

                "by": "system",

                "date":
                    datetime.utcnow()
                    .isoformat()
            }
        ]
    }

    receipts = get_receipts()

    # =====================================
    # DUPLICATE DETECTION
    # =====================================
    possible_duplicate = None

    for existing in receipts:

        if (

            str(existing.get("vendor", "")).lower().strip()
            ==
            str(receipt_record.get("vendor", "")).lower().strip()

            and

            float(existing.get("amount", 0))
            ==
            float(receipt_record.get("amount", 0))

            and

            str(existing.get("date", "")).strip()
            ==
            str(receipt_record.get("date", "")).strip()

        ):

            possible_duplicate = existing["id"]
            break

    if possible_duplicate:

        receipt_record["possible_duplicate"] = True

        receipt_record["duplicate_of"] = (
            possible_duplicate
        )

        receipt_record["status"] = "Needs Review"

        receipt_record["needs_review"] = True

    else:

        receipt_record["possible_duplicate"] = False

        receipt_record["duplicate_of"] = None

    receipts.append(receipt_record)

    save_receipts(receipts)

    return {
        "success": True,
        "receipt": receipt_record
    }

@router.get("/all")
async def get_all_receipts():

    return get_receipts()


# =====================================
# ✅ NEW: UPDATE + LEARNING
# =====================================


@router.put("/update/{receipt_id}")
async def update_receipt(

    receipt_id: str,

    updated_data: dict = Body(...)
):

    receipts = get_receipts()

    for r in receipts:

        if r["id"] == receipt_id:

            # =========================
            # UPDATE VALUES
            # =========================
            r["vendor"] = (
                updated_data.get(
                    "vendor",
                    r["vendor"]
                )
                .lower()
                .strip()
            )

            r["amount"] = (
                updated_data.get(
                    "amount",
                    r["amount"]
                )
            )

            r["category"] = (
            updated_data.get(
             "category",
           r["category"]
        )
     )

# Keep deduction synced with category
            r["deduction_type"] = r["category"]

            r["date"] = (
                updated_data.get(
                    "date",
                    r["date"]
                )
            )

            # =========================
            # LEARNING SYSTEM
            # =========================
            save_vendor_correction(

    r["vendor"],

    r["category"],

    r["category"]
)

            # =========================
            # REVIEW WORKFLOW
            # =========================
            r["vendor_learned"] = True

            r["manually_edited"] = True

            r["needs_review"] = False

            r["ai_confidence"] = "reviewed"

            r["status"] = "Reviewed"

            # =========================
            # AUDIT TRAIL
            # =========================
            r["audit_log"].append({

                "action": "manually_updated",

                "by": "user",

                "date":
                    datetime.utcnow()
                    .isoformat()
            })

    save_receipts(receipts)

    return {"success": True}


@router.put("/approve/{receipt_id}")
async def approve_receipt(
    receipt_id: str
):

    receipts = get_receipts()

    for r in receipts:

        if r["id"] == receipt_id:

            r["status"] = "Approved"

            success = xero_create_bill(r)

            if success:

                r["xero_synced"] = True

            r["audit_log"].append({

                "action": "approved",

                "by": "user",

                "date":
                    datetime.utcnow()
                    .isoformat()
            })

    save_receipts(receipts)

    return {"success": True}

@router.put("/approve-duplicate/{receipt_id}")
async def approve_duplicate(
    receipt_id: str
):

    receipts = get_receipts()

    for r in receipts:

        if r["id"] == receipt_id:

            r["status"] = "Approved"

            r["possible_duplicate"] = False

            r["needs_review"] = False

            r["audit_log"].append({

                "action": "duplicate_approved",

                "by": "user",

                "date":
                    datetime.utcnow()
                    .isoformat()
            })

    save_receipts(receipts)

    return {"success": True}


@router.put("/mark-duplicate/{receipt_id}")
async def mark_duplicate(
    receipt_id: str
):

    receipts = get_receipts()

    for r in receipts:

        if r["id"] == receipt_id:

            r["status"] = "Duplicate"

            r["audit_log"].append({

                "action": "marked_duplicate",

                "by": "user",

                "date":
                    datetime.utcnow()
                    .isoformat()
            })

    save_receipts(receipts)

    return {"success": True}

@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str
):

    receipts = get_receipts()

    new_receipts = []

    deleted_file = None

    for r in receipts:

        if r["id"] == receipt_id:

            deleted_file = r["filename"]

        else:

            new_receipts.append(r)

    if deleted_file:

        file_path = os.path.join(
            UPLOAD_FOLDER,
            deleted_file
        )

        if os.path.exists(file_path):

            os.remove(file_path)

    save_receipts(new_receipts)

    return {
        "success": True,
        "receipts": new_receipts
    }