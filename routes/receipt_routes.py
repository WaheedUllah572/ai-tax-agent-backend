
from fastapi import APIRouter, UploadFile, File, Body, Depends, HTTPException
import uuid
from datetime import datetime
import os
import shutil

from dependencies.auth_dependency import get_current_user
from services.aiAnalyzer import analyze_receipt_image
from services.irs_rules import apply_tax_rules
from fastapi.responses import FileResponse
from models.storage import (
    get_settings,
    get_receipts,
    save_receipts,
    save_vendor_correction,
)
from services.currency_service import convert_to_usd
from routes.xero_routes import xero_create_bill

router = APIRouter(prefix="/receipts", tags=["Receipts"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_user_receipt(receipts, receipt_id, user_id):
    for receipt in receipts:
        if (
            str(receipt.get("id")) == str(receipt_id)
            and str(receipt.get("user_id", "")) == str(user_id)
        ):
            return receipt
    return None


@router.get("/image/{filename}")
async def get_receipt_image(
    filename: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()

    receipt = next(
        (
            r for r in receipts
            if r.get("filename") == filename
            and str(r.get("user_id", "")) == str(current_user.id)
        ),
        None,
    )

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(filename))

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Receipt image not found.")

    return FileResponse(file_path)


@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with open(file_path, "rb") as uploaded_file:
            contents = uploaded_file.read()

        analyzed_data = await analyze_receipt_image(contents)

        converted_amount = convert_to_usd(
            analyzed_data.get("amount"),
            analyzed_data.get("currency"),
        )

        settings = get_settings() or {}
        irs_data = apply_tax_rules(
            analyzed_data.get("category"),
            converted_amount,
            settings.get("jurisdiction", "US"),
        )

        now = datetime.utcnow().isoformat()

        receipt_record = {
            "user_id": str(current_user.id),
            "id": str(uuid.uuid4()),
            "filename": unique_filename,
            "uploaded_at": now,
            "vendor": analyzed_data.get("vendor"),
            "date": analyzed_data.get("date"),
            "amount": analyzed_data.get("amount"),
            "currency": analyzed_data.get("currency", "USD"),
            "usd_amount": converted_amount,
            "category": analyzed_data.get("category"),
            "document_type": analyzed_data.get("document_type"),
            "deduction_type": analyzed_data.get("deduction_type"),
            "vendor_learned": analyzed_data.get("vendor_learned", False),
            "status": (
                "Needs Review"
                if analyzed_data.get("needs_review")
                else "Pending"
            ),
            "source": "upload",
            "ai_extracted": True,
            "ai_confidence": analyzed_data.get("ai_confidence", "low"),
            "needs_review": analyzed_data.get("needs_review", False),
            "is_blurry": analyzed_data.get("is_blurry", False),
            "blur_score": analyzed_data.get("blur_score", 0),
            "is_dark": analyzed_data.get("is_dark", False),
            "manually_edited": False,
            "irs_category": irs_data["irs_category"],
            "deductible_percent": irs_data["deductible_percent"],
            "deductible_amount": irs_data["deductible_amount"],
            "rule_applied": irs_data["rule_applied"],
            "jurisdiction": irs_data["jurisdiction"],
            "xero_synced": False,
            "locked": False,
            "possible_duplicate": False,
            "duplicate_of": None,
            "audit_log": [
                {"action": "created", "by": "system", "date": now}
            ],
        }

        receipts = get_receipts()
        if not isinstance(receipts, list):
            raise HTTPException(
                status_code=500,
                detail="Receipt storage returned an invalid format.",
            )

        # Only compare records owned by the current user.
        for existing in receipts:
            if str(existing.get("user_id", "")) != str(current_user.id):
                continue

            try:
                same_amount = float(existing.get("amount") or 0) == float(
                    receipt_record.get("amount") or 0
                )
            except (TypeError, ValueError):
                same_amount = False

            if (
                str(existing.get("vendor", "")).lower().strip()
                == str(receipt_record.get("vendor", "")).lower().strip()
                and same_amount
                and str(existing.get("date", "")).strip()
                == str(receipt_record.get("date", "")).strip()
            ):
                receipt_record["possible_duplicate"] = True
                receipt_record["duplicate_of"] = existing.get("id")
                receipt_record["status"] = "Needs Review"
                receipt_record["needs_review"] = True
                break

        receipts.append(receipt_record)
        save_receipts(receipts)

        return {"success": True, "receipt": receipt_record}

    except Exception:
        # Remove the newly uploaded file if processing failed.
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise


@router.get("/all")
async def get_all_receipts(
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    user_id = str(current_user.id)

    if not isinstance(receipts, list):
        print("RECEIPTS DIAGNOSTIC: storage did not return a list")
        raise HTTPException(
            status_code=500,
            detail="Receipt storage returned an invalid format.",
        )

    # Diagnostic logging: do not log receipt contents or sensitive data.
    matching_count = sum(
        1 for r in receipts
        if str(r.get("user_id", "")) == user_id
    )
    missing_owner_count = sum(
        1 for r in receipts
        if not r.get("user_id")
    )

    print("RECEIPTS DIAGNOSTIC - current user:", user_id)
    print("RECEIPTS DIAGNOSTIC - total stored:", len(receipts))
    print("RECEIPTS DIAGNOSTIC - matching user:", matching_count)
    print("RECEIPTS DIAGNOSTIC - records missing user_id:", missing_owner_count)

    # Keep tenant isolation enforced.
    return [
        r for r in receipts
        if str(r.get("user_id", "")) == user_id
    ]


@router.put("/update/{receipt_id}")
async def update_receipt(
    receipt_id: str,
    updated_data: dict = Body(...),
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    if receipt.get("locked", False):
        raise HTTPException(
            status_code=400,
            detail="Receipt is locked and cannot be edited.",
        )

    receipt["vendor"] = str(
        updated_data.get("vendor", receipt.get("vendor", "")) or ""
    ).lower().strip()
    receipt["amount"] = updated_data.get("amount", receipt.get("amount"))
    receipt["category"] = updated_data.get(
        "category", receipt.get("category")
    )
    receipt["deduction_type"] = receipt["category"]
    receipt["date"] = updated_data.get("date", receipt.get("date"))

    save_vendor_correction(
        receipt["vendor"],
        receipt["category"],
        receipt["category"],
    )

    receipt["vendor_learned"] = True
    receipt["manually_edited"] = True
    receipt["needs_review"] = False
    receipt["ai_confidence"] = "reviewed"
    receipt["status"] = "Reviewed"
    receipt.setdefault("audit_log", []).append({
        "action": "manually_updated",
        "by": "user",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.put("/notes/{receipt_id}")
async def save_receipt_note(
    receipt_id: str,
    data: dict = Body(...),
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt["accountant_note"] = data.get("note", "")
    receipt.setdefault("audit_log", []).append({
        "action": "note_added",
        "by": "accountant",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.put("/approve/{receipt_id}")
async def approve_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt["status"] = "Locked"
    receipt["locked"] = True

    if xero_create_bill(receipt):
        receipt["xero_synced"] = True

    receipt.setdefault("audit_log", []).append({
        "action": "approved",
        "by": "user",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.put("/approve-duplicate/{receipt_id}")
async def approve_duplicate(
    receipt_id: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt["status"] = "Locked"
    receipt["locked"] = True
    receipt["possible_duplicate"] = False
    receipt["needs_review"] = False
    receipt.setdefault("audit_log", []).append({
        "action": "duplicate_approved",
        "by": "user",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.put("/mark-duplicate/{receipt_id}")
async def mark_duplicate(
    receipt_id: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt["status"] = "Duplicate"
    receipt["possible_duplicate"] = False
    receipt["needs_review"] = False
    receipt.setdefault("audit_log", []).append({
        "action": "marked_duplicate",
        "by": "user",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.put("/reject/{receipt_id}")
async def reject_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    receipt["status"] = "Rejected"
    receipt["locked"] = False
    receipt.setdefault("audit_log", []).append({
        "action": "rejected",
        "by": "accountant",
        "date": datetime.utcnow().isoformat(),
    })

    save_receipts(receipts)
    return {"success": True}


@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user=Depends(get_current_user),
):
    receipts = get_receipts()
    receipt = get_user_receipt(receipts, receipt_id, current_user.id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")

    deleted_file = receipt.get("filename")

    new_receipts = [
        r for r in receipts
        if not (
            str(r.get("id")) == str(receipt_id)
            and str(r.get("user_id", "")) == str(current_user.id)
        )
    ]

    save_receipts(new_receipts)

    if deleted_file:
        file_path = os.path.join(UPLOAD_FOLDER, os.path.basename(deleted_file))
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    return {"success": True}
