from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import json
import requests
import secrets
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

router = APIRouter(prefix="/xero", tags=["Xero"])

XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI")

# =====================================================
# 🆕 SUPABASE CONNECTION
# =====================================================
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


# =====================================================
# TOKEN HELPERS (UPDATED TO SUPABASE)
# =====================================================
def save_tokens(data: dict):
    try:
        # delete old tokens (FIXED)
        supabase.table("xero_tokens").delete().gt("id", "").execute()

        # insert new tokens
        res = supabase.table("xero_tokens").insert({
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "tenant_id": data["tenant_id"],
            "tenant_name": data.get("tenant_name")
        }).execute()

        print("SUPABASE INSERT RESULT:", res)

    except Exception as e:
        print("SUPABASE ERROR:", str(e))


def load_tokens():
    res = supabase.table("xero_tokens").select("*").limit(1).execute()

    if not res.data:
        return None

    return res.data[0]


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
        return None

    new_tokens["tenant_id"] = tokens["tenant_id"]
    new_tokens["tenant_name"] = tokens.get("tenant_name")
    save_tokens(new_tokens)
    return new_tokens


def xero_get(endpoint: str):
    tokens = load_tokens()
    if not tokens:
        return None

    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Xero-tenant-id": tokens["tenant_id"],
        "Accept": "application/json",
    }

    url = f"https://api.xero.com/api.xro/2.0/{endpoint}"
    res = requests.get(url, headers=headers)

    # 🔁 Auto refresh on expiry
    if res.status_code in (401, 403):
        tokens = refresh_xero_token()
        if not tokens:
            return None

        headers["Authorization"] = f"Bearer {tokens['access_token']}"
        headers["Xero-tenant-id"] = tokens["tenant_id"]

        res = requests.get(url, headers=headers)

    if res.status_code != 200:
        print("Xero API error:", res.status_code, res.text)
        return None

    return res.json()


# =====================================================
# OAUTH
# =====================================================
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
        return JSONResponse({"error": "Missing code"}, 400)

    token_url = "https://identity.xero.com/connect/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": XERO_REDIRECT_URI,
        "client_id": XERO_CLIENT_ID,
        "client_secret": XERO_CLIENT_SECRET,
    }

    tokens = requests.post(token_url, data=payload).json()

    if "access_token" not in tokens:
        return JSONResponse({"error": "Token exchange failed"}, 400)

    tenants = requests.get(
        "https://api.xero.com/connections",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).json()

    if not tenants:
        return JSONResponse({"error": "No tenants found"}, 400)

    tenant = None
    for t in tenants:
        if t.get("tenantName"):
            tenant = t
            break

    if not tenant:
        return JSONResponse({"error": "No valid tenant found"}, 400)

    tokens["tenant_id"] = tenant["tenantId"]
    tokens["tenant_name"] = tenant["tenantName"]

    save_tokens(tokens)

    return {"connected": True, "tenant": tenant["tenantName"]}


# =====================================================
# STATUS
# =====================================================
@router.get("/status")
async def xero_status():
    return {"connected": bool(load_tokens())}


# =====================================================
# DATA ROUTES
# =====================================================
@router.get("/customers")
async def xero_customers():
    data = xero_get("Contacts")
    return {"customers": data.get("Contacts", []) if data else []}


@router.get("/contacts")
async def xero_contacts():
    data = xero_get("Contacts")
    return {"customers": data.get("Contacts", []) if data else []}


@router.get("/invoices")
async def xero_invoices():
    data = xero_get("Invoices")
    return {"invoices": data.get("Invoices", []) if data else []}


@router.get("/accounts")
async def xero_accounts():
    data = xero_get("Accounts")
    return {"accounts": data.get("Accounts", []) if data else []}