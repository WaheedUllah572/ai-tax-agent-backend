from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import secrets
from dotenv import load_dotenv
import uuid
from datetime import datetime

from gmail_utils import save_tokens, load_tokens, scan_receipts_by_year
from models.storage import (
    get_receipts,
    save_receipts,
    get_settings
)
from services.irs_rules import apply_tax_rules

load_dotenv()

router = APIRouter(prefix="/gmail", tags=["Gmail"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


@router.get("/connect")
async def gmail_connect():
    state = secrets.token_urlsafe(16)
    scope = "https://www.googleapis.com/auth/gmail.readonly"

    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )

    return RedirectResponse(url)


@router.get("/callback")
async def gmail_callback(request: Request):
    code = request.query_params.get("code")

    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    tokens = requests.post(token_url, data=data).json()

    if "access_token" not in tokens:
        return JSONResponse(tokens, status_code=400)

    if "expires_in" in tokens:
        import time
        tokens["expires_at"] = time.time() + tokens["expires_in"]

    save_tokens(tokens)

    return {"message": "Gmail connected successfully"}


@router.get("/status")
async def gmail_status():
    tokens = load_tokens()

    return {
        "connected": tokens is not None,
        "has_refresh_token": tokens is not None and "refresh_token" in tokens,
    }


@router.get("/scan")
async def gmail_scan():

    current_year = datetime.utcnow().year
    years = [current_year - i for i in range(5)]

    receipts = get_receipts()
    imported = []

    existing_message_ids = {r.get("message_id") for r in receipts}

    for year in years:
        results = scan_receipts_by_year(year)

        for r in results:
            message_id = r.get("message_id")

            if message_id in existing_message_ids:
                continue

            data = r.get("analysis", {})

            # APPLY TAX RULES

            settings = get_settings()

            irs_data = apply_tax_rules(
                data.get("category"),
                data.get("amount"),
                settings.get(
                    "jurisdiction",
                    "US"
                )
            )

            receipt_record = { 
                "id": str(uuid.uuid4()),
                "message_id": message_id,
                "filename": r.get("filename", "email_receipt"),
                "uploaded_at": datetime.utcnow().isoformat(),
                "vendor": data.get("vendor", "Unknown"),
                "date": data.get("date", ""),
                "amount": data.get("amount", "0.00"),
                "category": data.get("category", "Business Expense"),
                "document_type": data.get("document_type", "Email Receipt"),
                "deduction_type": data.get("deduction_type", "General Business Expense"),
                "status": "Pending",

                # NEW FIELDS
                "source": "gmail",
                "ai_extracted": True,
                "ai_confidence": data.get("ai_confidence", "low"),
                "manually_edited": False,

                # IRS RULES
                "irs_category": irs_data["irs_category"],
                "deductible_percent": irs_data["deductible_percent"],
                "deductible_amount": irs_data["deductible_amount"],
                "rule_applied": irs_data["rule_applied"],

                "audit_log": [
                    {
                        "action": "created_from_gmail",
                        "by": "system",
                        "date": datetime.utcnow().isoformat()
                    }
                ]
            }

            receipts.append(receipt_record)
            imported.append(receipt_record)

    save_receipts(receipts)

    return {
        "success": True,
        "imported": len(imported),
        "receipts": imported
    }