from fastapi import APIRouter, UploadFile, File, Body
import uuid
from datetime import datetime
import os
import shutil
from fastapi import Depends
from dependencies.auth_dependency import get_current_user
from services.aiAnalyzer import analyze_receipt_image
from services.irs_rules import apply_tax_rules
from database import supabase_admin
from fastapi.responses import FileResponse
from models.storage import (
    get_settings,
    get_receipts,
    save_receipts,
    save_vendor_correction
)

from services.currency_service import convert_to_usd
from routes.xero_routes import xero_create_bill

router = APIRouter(prefix="/receipts", tags=["Receipts"])
def get_user_receipt(receipts, receipt_id, user_id):
    for receipt in receipts:
        if (
            str(receipt.get("id")) == str(receipt_id)
            and str(receipt.get("user_id")) == str(user_id)
        ):
            return receipt

    return None

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.get("/image/{filename}")
async def get_receipt_image(
    filename: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = next(
        (
            r for r in receipts
            if r.get("filename") == filename
            and str(r.get("user_id")) == str(current_user.id)
        ),
        None
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    if not os.path.isfile(file_path):
        return {
            "success": False,
            "message": "Receipt image not found."
        }

    return FileResponse(file_path)


@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):

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

    settings = get_settings()

    irs_data = apply_tax_rules(
    analyzed_data.get("category"),
    converted_amount,
    settings.get(
        "jurisdiction",
        "US"
    )
)
    print("DEBUG IRS DATA:", irs_data)

    receipt_record = {

        "user_id": str(current_user.id),

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

"jurisdiction":
    irs_data["jurisdiction"],

        "xero_synced": False,
        "locked": False,

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

        # Only compare receipts belonging to the same user
        if str(existing.get("user_id")) != str(current_user.id):
            continue

        if (
            str(existing.get("vendor", "")).lower().strip()
            == str(receipt_record.get("vendor", "")).lower().strip()
            and
            float(existing.get("amount", 0))
            == float(receipt_record.get("amount", 0))
            and
            str(existing.get("date", "")).strip()
            == str(receipt_record.get("date", "")).strip()
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

    print("DEBUG RECEIPT:", receipt_record)
    receipts.append(receipt_record)

    save_receipts(receipts)

    return {
        "success": True,
        "receipt": receipt_record
    }

@router.get("/all")
async def get_all_receipts(
    current_user=Depends(get_current_user)
):
    receipts = get_receipts()

    user_receipts = [
        r for r in receipts
        if str(r.get("user_id")) == str(current_user.id)
    ]

    return user_receipts


# =====================================
# ✅ NEW: UPDATE + LEARNING
# =====================================


@router.put("/update/{receipt_id}")
async def update_receipt(
    receipt_id: str,
    updated_data: dict = Body(...),
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    if receipt.get("locked", False):
        return {
            "success": False,
            "message": "Receipt is locked and cannot be edited."
        }

    receipt["vendor"] = (
        updated_data.get(
            "vendor",
            receipt.get("vendor", "")
        )
        .lower()
        .strip()
    )

    receipt["amount"] = updated_data.get(
        "amount",
        receipt.get("amount")
    )

    receipt["category"] = updated_data.get(
        "category",
        receipt.get("category")
    )

    # Keep deduction synced with category
    receipt["deduction_type"] = receipt["category"]

    receipt["date"] = updated_data.get(
        "date",
        receipt.get("date")
    )

    save_vendor_correction(
        receipt["vendor"],
        receipt["category"],
        receipt["category"]
    )

    receipt["vendor_learned"] = True
    receipt["manually_edited"] = True
    receipt["needs_review"] = False
    receipt["ai_confidence"] = "reviewed"
    receipt["status"] = "Reviewed"

    receipt.setdefault("audit_log", []).append({
        "action": "manually_updated",
        "by": "user",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }

@router.put("/notes/{receipt_id}")
async def save_receipt_note(
    receipt_id: str,
    data: dict = Body(...),
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    receipt["accountant_note"] = data.get("note", "")

    receipt.setdefault("audit_log", []).append({
        "action": "note_added",
        "by": "accountant",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }


@router.put("/approve/{receipt_id}")
async def approve_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    receipt["status"] = "Locked"
    receipt["locked"] = True

    success = xero_create_bill(receipt)

    if success:
        receipt["xero_synced"] = True

    receipt.setdefault("audit_log", []).append({
        "action": "approved",
        "by": "user",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }

@router.put("/approve-duplicate/{receipt_id}")
async def approve_duplicate(
    receipt_id: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    receipt["status"] = "Locked"
    receipt["locked"] = True
    receipt["possible_duplicate"] = False
    receipt["needs_review"] = False

    receipt.setdefault("audit_log", []).append({
        "action": "duplicate_approved",
        "by": "user",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }


@router.put("/mark-duplicate/{receipt_id}")
async def mark_duplicate(
    receipt_id: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    receipt["status"] = "Duplicate"
    receipt["possible_duplicate"] = False
    receipt["needs_review"] = False

    receipt.setdefault("audit_log", []).append({
        "action": "marked_duplicate",
        "by": "user",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }

@router.put("/reject/{receipt_id}")
async def reject_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    receipt["status"] = "Rejected"
    receipt["locked"] = False

    receipt.setdefault("audit_log", []).append({
        "action": "rejected",
        "by": "accountant",
        "date": datetime.utcnow().isoformat()
    })

    save_receipts(receipts)

    return {
        "success": True
    }

@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()

    receipt = get_user_receipt(
        receipts,
        receipt_id,
        current_user.id
    )

    if not receipt:
        return {
            "success": False,
            "message": "Receipt not found."
        }

    deleted_file = receipt.get("filename")

    new_receipts = [
        r for r in receipts
        if str(r.get("id")) != str(receipt_id)
        or str(r.get("user_id")) != str(current_user.id)
    ]

    if deleted_file:
        file_path = os.path.join(
            UPLOAD_FOLDER,
            deleted_file
        )

        if os.path.exists(file_path):
            os.remove(file_path)

    save_receipts(new_receipts)

    return {
        "success": True
    }