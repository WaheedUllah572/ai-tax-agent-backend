from fastapi import APIRouter, UploadFile, File
import uuid
from datetime import datetime
import os
import shutil

from services.aiAnalyzer import analyze_receipt_image
from services.irs_rules import apply_irs_rules
from models.storage import get_receipts, save_receipts

router = APIRouter(prefix="/receipts", tags=["Receipts"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(file_path, "rb") as f:
        contents = f.read()

    analyzed_data = await analyze_receipt_image(contents)

    # APPLY IRS RULES
    irs_data = apply_irs_rules(
        analyzed_data.get("category"),
        analyzed_data.get("amount")
    )

    receipt_record = {
        "id": str(uuid.uuid4()),
        "filename": unique_filename,
        "uploaded_at": datetime.utcnow().isoformat(),
        "vendor": analyzed_data.get("vendor"),
        "date": analyzed_data.get("date"),
        "amount": analyzed_data.get("amount"),
        "category": analyzed_data.get("category"),
        "document_type": analyzed_data.get("document_type"),
        "deduction_type": analyzed_data.get("deduction_type", "Uncategorized"),
        "status": "Pending",

        # NEW FIELDS
        "source": "upload",
        "ai_extracted": True,
        "ai_confidence": analyzed_data.get("ai_confidence", "low"),
        "manually_edited": False,

        # IRS RULES
        "irs_category": irs_data["irs_category"],
        "deductible_percent": irs_data["deductible_percent"],
        "deductible_amount": irs_data["deductible_amount"],
        "rule_applied": irs_data["rule_applied"],

        "audit_log": [
            {
                "action": "created",
                "by": "system",
                "date": datetime.utcnow().isoformat()
            }
        ]
    }

    receipts = get_receipts()
    receipts.append(receipt_record)
    save_receipts(receipts)

    return {
        "success": True,
        "receipt": receipt_record
    }


@router.get("/all")
async def get_all_receipts():
    return get_receipts()


@router.put("/approve/{receipt_id}")
async def approve_receipt(receipt_id: str):

    receipts = get_receipts()

    for r in receipts:
        if r["id"] == receipt_id:
            r["status"] = "Approved"
            r["audit_log"].append({
                "action": "approved",
                "by": "user",
                "date": datetime.utcnow().isoformat()
            })

    save_receipts(receipts)

    return {"success": True}


@router.put("/update/{receipt_id}")
async def update_receipt(receipt_id: str, data: dict):

    receipts = get_receipts()

    for r in receipts:
        if r["id"] == receipt_id:
            r["vendor"] = data.get("vendor", r["vendor"])
            r["date"] = data.get("date", r["date"])
            r["amount"] = data.get("amount", r["amount"])
            r["category"] = data.get("category", r["category"])
            r["document_type"] = data.get("document_type", r["document_type"])

            r["manually_edited"] = True
            r["audit_log"].append({
                "action": "edited",
                "by": "user",
                "date": datetime.utcnow().isoformat()
            })

    save_receipts(receipts)

    return {"success": True}


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str):

    receipts = get_receipts()

    updated = []
    deleted_file = None

    for r in receipts:
        if r["id"] == receipt_id:
            deleted_file = r["filename"]
        else:
            updated.append(r)

    if deleted_file:
        file_path = os.path.join(UPLOAD_FOLDER, deleted_file)
        if os.path.exists(file_path):
            os.remove(file_path)

    save_receipts(updated)

    return {"success": True}