from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import secrets
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta
load_dotenv()

router = APIRouter(prefix="/xero", tags=["Xero"])

XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ================= TOKEN HELPERS =================

def save_tokens(data: dict):
    try:
        supabase.table("xero_tokens").delete().neq(
            "id", "00000000-0000-0000-0000-000000000000"
        ).execute()

        supabase.table("xero_tokens").insert({
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "tenant_id": data["tenant_id"],
            "tenant_name": data.get("tenant_name")
        }).execute()

    except Exception as e:
        print("SUPABASE ERROR:", str(e))


def load_tokens():
    try:
        res = supabase.table("xero_tokens").select("*").limit(1).execute()

        if not res.data:
            return None

        return res.data[0]

    except Exception as e:
        print("SUPABASE LOAD ERROR:", str(e))
        return None


def refresh_xero_token():

    tokens = load_tokens()

    if not tokens:
        return None

    url = "https://identity.xero.com/connect/token"

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": XERO_CLIENT_ID,
        "client_secret": XERO_CLIENT_SECRET,
    }

    res = requests.post(url, data=payload)

    new_tokens = res.json()

    if "access_token" not in new_tokens:
        print("TOKEN REFRESH FAILED:", new_tokens)
        return None

    new_tokens["tenant_id"] = tokens["tenant_id"]
    new_tokens["tenant_name"] = tokens.get("tenant_name")

    save_tokens(new_tokens)

    return new_tokens


def get_headers():

    tokens = load_tokens()

    if not tokens:
        return None

    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Xero-tenant-id": tokens["tenant_id"],
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


# ================= CREATE BILL =================

def xero_create_bill(receipt: dict):

    headers = get_headers()

    if not headers:
        return False

    url = "https://api.xero.com/api.xro/2.0/Invoices"

    # Get receipt date and calculate due date
    receipt_date = receipt.get("date")

    if receipt_date:
        try:
            parsed_date = datetime.strptime(receipt_date, "%Y-%m-%d")
        except ValueError:
            parsed_date = datetime.utcnow()
    else:
        parsed_date = datetime.utcnow()

    due_date = parsed_date + timedelta(days=30)

    # Create Xero bill
    payload = {
        "Type": "ACCPAY",

        "Contact": {
            "Name": receipt.get("vendor", "Unknown Vendor")
        },

        "Date": parsed_date.strftime("%Y-%m-%d"),

        "DueDate": due_date.strftime("%Y-%m-%d"),

        "LineItems": [
            {
                "Description": receipt.get("category", "Expense"),
                "Quantity": 1,
                "UnitAmount": float(receipt.get("amount", 0)),
                "AccountCode": "400"
            }
        ],

        "Status": "AUTHORISED"
    }

    # First attempt
    res = requests.post(
        url,
        json=payload,
        headers=headers
    )

    # If Xero access token expired, refresh and retry once
    if res.status_code == 401:

        print("XERO TOKEN EXPIRED - REFRESHING")

        new_tokens = refresh_xero_token()

        if not new_tokens:
            print("XERO TOKEN REFRESH FAILED")
            return False

        headers = get_headers()

        if not headers:
            return False

        res = requests.post(
            url,
            json=payload,
            headers=headers
        )

    # Check Xero response
    if res.status_code not in (200, 201):

        print(
            "XERO CREATE BILL ERROR:",
            res.status_code,
            res.text
        )

        return False

    print("XERO BILL CREATED SUCCESSFULLY")

    return True


# ================= OAUTH =================

@router.get("/connect")
async def connect_xero():

    state = secrets.token_urlsafe(16)

    scopes = (
        "openid email profile "
        "offline_access "
        "accounting.settings "
        "accounting.transactions "
        "accounting.contacts "
        "accounting.journals.read"
    )

    url = (
        "https://login.xero.com/identity/connect/authorize"
        f"?response_type=code"
        f"&client_id={XERO_CLIENT_ID}"
        f"&redirect_uri={XERO_REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={state}"
    )

    return RedirectResponse(url)


@router.get("/callback")
async def xero_callback(request: Request):

    code = request.query_params.get("code")

    if not code:
        return JSONResponse(
            {"error": "Missing code"},
            400
        )

    token_url = "https://identity.xero.com/connect/token"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": XERO_REDIRECT_URI,
        "client_id": XERO_CLIENT_ID,
        "client_secret": XERO_CLIENT_SECRET,
    }

    tokens = requests.post(
        token_url,
        data=payload
    ).json()

    if "access_token" not in tokens:
        return JSONResponse(
            {"error": "Token exchange failed"},
            400
        )

    tenants = requests.get(
        "https://api.xero.com/connections",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        },
    ).json()

    if not tenants:
        return JSONResponse(
            {"error": "No tenants found"},
            400
        )

    tenant = tenants[0]

    tokens["tenant_id"] = tenant["tenantId"]
    tokens["tenant_name"] = tenant["tenantName"]

    save_tokens(tokens)

    return {
        "connected": True,
        "tenant": tenant["tenantName"]
    }


@router.get("/status")
async def xero_status():

    return {
        "connected": bool(load_tokens())
    }


# ================= CUSTOMERS =================

@router.get("/customers")
async def get_customers():

    headers = get_headers()

    if not headers:
        return JSONResponse(
            {"error": "Not connected"},
            401
        )

    url = "https://api.xero.com/api.xro/2.0/Contacts"

    res = requests.get(
        url,
        headers=headers
    )

    if res.status_code != 200:
        print("CUSTOMERS ERROR:", res.text)

        return JSONResponse(
            {"error": "Failed to fetch customers"},
            400
        )

    data = res.json()

    return data.get("Contacts", [])


# ================= INVOICES =================

@router.get("/invoices")
async def get_invoices():

    headers = get_headers()

    if not headers:
        return JSONResponse(
            {"error": "Not connected"},
            401
        )

    url = "https://api.xero.com/api.xro/2.0/Invoices"

    res = requests.get(
        url,
        headers=headers
    )

    if res.status_code != 200:
        print("INVOICES ERROR:", res.text)

        return JSONResponse(
            {"error": "Failed to fetch invoices"},
            400
        )

    data = res.json()

    return data.get("Invoices", [])


# ================= ACCOUNTS =================

@router.get("/accounts")
async def get_accounts():

    headers = get_headers()

    if not headers:
        return JSONResponse(
            {"error": "Not connected"},
            401
        )

    url = "https://api.xero.com/api.xro/2.0/Accounts"

    res = requests.get(
        url,
        headers=headers
    )

    if res.status_code != 200:
        print("ACCOUNTS ERROR:", res.text)

        return JSONResponse(
            {"error": "Failed to fetch accounts"},
            400
        )

    data = res.json()

    return data.get("Accounts", [])