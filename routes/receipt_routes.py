from fastapi import APIRouter, UploadFile, File
import uuid
from datetime import datetime
import os
import shutil

from services.aiAnalyzer import analyze_receipt_image
from services.irs_rules import apply_irs_rules
from models.storage import get_receipts, save_receipts

from routes.xero_routes import xero_create_bill

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
        "currency": analyzed_data.get("currency", "USD"),  # ✅ FIX
        "category": analyzed_data.get("category"),
        "document_type": analyzed_data.get("document_type"),

        # ✅ HUMAN READABLE
        "deduction_type": irs_data["irs_category"],

        "status": "Pending",

        "source": "upload",
        "ai_extracted": True,
        "ai_confidence": analyzed_data.get("ai_confidence", "low"),
        "manually_edited": False,

        "irs_category": irs_data["irs_category"],
        "deductible_percent": irs_data["deductible_percent"],
        "deductible_amount": irs_data["deductible_amount"],
        "rule_applied": irs_data["rule_applied"],

        "xero_synced": False,

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

    return {"success": True, "receipt": receipt_record}


@router.get("/all")
async def get_all_receipts():
    return get_receipts()


@router.put("/approve/{receipt_id}")
async def approve_receipt(receipt_id: str):

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
                "date": datetime.utcnow().isoformat()
            })

    save_receipts(receipts)

    return {"success": True}


@router.delete("/{receipt_id}")
async def delete_receipt(receipt_id: str):

    receipts = get_receipts()

    new_receipts = []
    deleted_file = None

    for r in receipts:
        if r["id"] == receipt_id:
            deleted_file = r["filename"]
        else:
            new_receipts.append(r)

    if deleted_file:
        file_path = os.path.join(UPLOAD_FOLDER, deleted_file)
        if os.path.exists(file_path):
            os.remove(file_path)

    save_receipts(new_receipts)

    return {"success": True, "receipts": new_receipts}