from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
TOKEN_PATH = "gmail_token.json"

@router.get("/connect")
async def gmail_connect():
    """
    Step 1: Redirect user to Google OAuth consent screen.
    """
    scope = "https://www.googleapis.com/auth/gmail.readonly"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
async def gmail_callback(request: Request):
    """
    Step 2: Google redirects back with ?code=XYZ
    Exchange it for access & refresh tokens.
    """
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "No authorization code received"}, status_code=400)

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=data)
    tokens = response.json()

    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=4)

    return JSONResponse({"message": "✅ Gmail connected successfully!", "tokens_saved": True})


@router.get("/profile")
async def gmail_profile():
    """
    Step 3: Use stored token to fetch Gmail profile info.
    """
    if not os.path.exists(TOKEN_PATH):
        return JSONResponse({"error": "No Gmail token found. Connect first."}, status_code=404)

    with open(TOKEN_PATH, "r") as f:
        tokens = json.load(f)

    access_token = tokens.get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.googleapis.com/gmail/v1/users/me/profile", headers=headers)

    if response.status_code != 200:
        return JSONResponse({"error": "Failed to fetch Gmail profile.", "details": response.json()}, status_code=400)

    return response.json()
