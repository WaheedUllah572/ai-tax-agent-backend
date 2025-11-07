from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

QB_CLIENT_ID = os.getenv("QB_CLIENT_ID")
QB_CLIENT_SECRET = os.getenv("QB_CLIENT_SECRET")
QB_REDIRECT_URI = os.getenv("QB_REDIRECT_URI")
TOKEN_PATH = "quickbook_tokens.json"

@router.get("/connect")
async def quickbooks_connect():
    """
    Step 1: Redirect user to QuickBooks OAuth consent page.
    """
    auth_url = (
        f"https://appcenter.intuit.com/connect/oauth2"
        f"?client_id={QB_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=com.intuit.quickbooks.accounting"
        f"&redirect_uri={QB_REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
async def quickbooks_callback(request: Request):
    """
    Step 2: QuickBooks redirects with ?code=XYZ
    Exchange for tokens and save locally.
    """
    code = request.query_params.get("code")
    realm_id = request.query_params.get("realmId")
    if not code:
        return JSONResponse({"error": "No authorization code received"}, status_code=400)

    token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    auth_header = requests.auth.HTTPBasicAuth(QB_CLIENT_ID, QB_CLIENT_SECRET)

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": QB_REDIRECT_URI,
    }

    response = requests.post(token_url, auth=auth_header, data=data)
    tokens = response.json()
    tokens["realm_id"] = realm_id

    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=4)

    return JSONResponse({"message": "✅ QuickBooks connected successfully!", "tokens_saved": True})


@router.get("/profile")
async def quickbooks_profile():
    """
    Example endpoint to fetch QuickBooks company info.
    """
    if not os.path.exists(TOKEN_PATH):
        return JSONResponse({"error": "No QuickBooks token found."}, status_code=404)

    with open(TOKEN_PATH, "r") as f:
        tokens = json.load(f)

    access_token = tokens.get("access_token")
    realm_id = tokens.get("realm_id")

    if not access_token or not realm_id:
        return JSONResponse({"error": "Invalid or missing token data."}, status_code=400)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    api_url = f"https://quickbooks.api.intuit.com/v3/company/{realm_id}/companyinfo/{realm_id}"
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return JSONResponse({"error": "Failed to fetch QuickBooks data.", "details": response.json()}, status_code=400)

    return response.json()
