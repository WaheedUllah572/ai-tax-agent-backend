import os
import json
import base64
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_PATH = "gmail_token.json"


def save_tokens(tokens: dict):
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=4)


def load_tokens():
    if not os.path.exists(TOKEN_PATH):
        return None

    with open(TOKEN_PATH, "r") as f:
        return json.load(f)


def refresh_gmail_token():
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        return None

    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }

    res = requests.post(url, data=data).json()

    if "access_token" not in res:
        return None

    if "expires_in" in res:
        res["expires_at"] = time.time() + res["expires_in"]

    save_tokens(res)
    return res


def get_valid_access_token():
    tokens = load_tokens()
    if not tokens:
        return None

    if "expires_at" not in tokens or time.time() > tokens["expires_at"]:
        new_tokens = refresh_gmail_token()
        if not new_tokens:
            return None
        return new_tokens["access_token"]

    return tokens["access_token"]


# FETCH MESSAGES
def fetch_messages():
    access_token = get_valid_access_token()
    if not access_token:
        return []

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

    all_messages = []
    next_page = None

    for _ in range(5):
        params = {
            "maxResults": 50,
            "q": "in:inbox has:attachment (subject:receipt OR subject:invoice OR from:uber OR from:amazon OR from:paypal OR from:stripe)"
        }

        if next_page:
            params["pageToken"] = next_page

        res = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        ).json()

        messages = res.get("messages", [])
        all_messages.extend(messages)
        next_page = res.get("nextPageToken")

        if not next_page:
            break

    return all_messages


def fetch_message_detail(msg_id):
    access_token = get_valid_access_token()
    if not access_token:
        return None

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"

    res = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    return res


def get_attachments(message_data):
    attachments = []

    def walk_parts(parts):
        for part in parts:
            filename = part.get("filename", "").lower()
            mime_type = part.get("mimeType", "")
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")

            # ONLY images
            if attachment_id and filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
                attachments.append({
                    "filename": filename,
                    "attachment_id": attachment_id
                })

            if "parts" in part:
                walk_parts(part["parts"])

    payload = message_data.get("payload", {})
    if "parts" in payload:
        walk_parts(payload["parts"])

    return attachments


def download_attachment(msg_id, attachment_id):
    access_token = get_valid_access_token()
    if not access_token:
        return None

    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/attachments/{attachment_id}"

    res = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    data = res.get("data")
    if not data:
        return None

    return base64.urlsafe_b64decode(data + "==")


def scan_receipts_by_year(year):
    from receipt_ai import analyze_receipt_image

    messages = fetch_messages()
    results = []

    for msg in messages:
        msg_id = msg["id"]

        details = fetch_message_detail(msg_id)
        if not details:
            continue

        attachments = get_attachments(details)
        if not attachments:
            continue

        for att in attachments:
            file_bytes = download_attachment(msg_id, att["attachment_id"])
            if not file_bytes:
                continue

            ocr_data = analyze_receipt_image(file_bytes)

            results.append({
                "analysis": ocr_data,
                "message_id": msg_id,
                "filename": att["filename"]
            })

    return results