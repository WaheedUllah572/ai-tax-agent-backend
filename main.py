from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import requests, os, datetime, json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
import openai

# ------------------ INITIAL SETUP ------------------ #
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------ GOOGLE SHEETS ------------------ #
scope = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
creds = Credentials.from_service_account_file("google-credentials.json", scopes=scope)
service = build("sheets", "v4", credentials=creds)
SPREADSHEET_ID = "1dl1o5gLriDLUeRmzDT_Oft-6RkQD76crmZDwYWviSOE"
sheet_title = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()["sheets"][0]["properties"]["title"]

def append_to_google_sheet(vendor, amount, category, txn_id, status="Success"):
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [[
            now,
            "Expense Log",
            vendor,
            datetime.date.today().isoformat(),
            category,
            amount,
            "",
            f"QB TxnID: {txn_id}",
            f"Expense synced successfully ({status})",
        ]]
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_title}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
    except Exception as e:
        print(f"⚠️ Google Sheet append failed: {e}")

# ------------------ FASTAPI APP ------------------ #
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "https://symbols-superb-icons-exhibitions.trycloudflare.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ QUICKBOOKS CONFIG ------------------ #
QB_CLIENT_ID = os.getenv("QB_CLIENT_ID")
QB_CLIENT_SECRET = os.getenv("QB_CLIENT_SECRET")
QB_REDIRECT_URI = os.getenv("QB_REDIRECT_URI")
QB_ENVIRONMENT = os.getenv("QB_ENVIRONMENT", "sandbox")

auth_client = AuthClient(
    client_id=QB_CLIENT_ID,
    client_secret=QB_CLIENT_SECRET,
    environment=QB_ENVIRONMENT,
    redirect_uri=QB_REDIRECT_URI,
)

def load_tokens():
    if not os.path.exists("quickbook_tokens.json"):
        raise Exception("QuickBooks not connected.")
    with open("quickbook_tokens.json", "r") as f:
        return json.load(f)

def save_tokens(tokens):
    with open("quickbook_tokens.json", "w") as f:
        json.dump(tokens, f)

def refresh_access_token():
    try:
        tokens = load_tokens()
        auth_client.refresh(refresh_token=tokens["refresh_token"])
        tokens["access_token"] = auth_client.access_token
        tokens["refresh_token"] = auth_client.refresh_token
        save_tokens(tokens)
        print("✅ QuickBooks token refreshed successfully.")
        return tokens
    except Exception as e:
        raise Exception(f"Token refresh failed: {e}")

def get_auth_header():
    tokens = load_tokens()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

# ------------------ QUICKBOOKS ROUTES ------------------ #
@app.get("/quickbooks/connect")
def quickbooks_connect():
    try:
        url = auth_client.get_authorization_url(scopes=[Scopes.ACCOUNTING])
        return RedirectResponse(url)
    except Exception as e:
        return JSONResponse({"error": f"QuickBooks connect failed: {e}"}, status_code=500)

@app.get("/quickbooks/callback")
def quickbooks_callback(code: str, realmId: str):
    try:
        auth_client.get_bearer_token(code, realm_id=realmId)
        tokens = {
            "access_token": auth_client.access_token,
            "refresh_token": auth_client.refresh_token,
            "realm_id": realmId,
        }
        save_tokens(tokens)
        return JSONResponse({"status": "✅ QuickBooks Connected Successfully!"})
    except Exception as e:
        return JSONResponse({"error": f"Callback failed: {e}"}, status_code=500)

@app.get("/quickbooks/status")
def quickbooks_status():
    try:
        tokens = load_tokens()
        realm_id = tokens["realm_id"]
        url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/companyinfo/{realm_id}"
        r = requests.get(url, headers=get_auth_header())
        if r.status_code == 401:
            refresh_access_token()
            r = requests.get(url, headers=get_auth_header())
        connected = r.status_code == 200
        return {"connected": connected, "status": "Connected" if connected else "Disconnected"}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@app.get("/quickbooks/companyinfo")
def quickbooks_companyinfo():
    try:
        tokens = load_tokens()
        realm_id = tokens["realm_id"]
        url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/companyinfo/{realm_id}"
        r = requests.get(url, headers=get_auth_header())
        if r.status_code == 401:
            refresh_access_token()
            r = requests.get(url, headers=get_auth_header())
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# 🔹 FIXED Query Endpoints (send plain text, not JSON)
def qb_query(sql):
    """Utility to handle QuickBooks SQL queries properly"""
    try:
        tokens = load_tokens()
        realm_id = tokens["realm_id"]
        url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/query"
        headers = get_auth_header()
        headers["Content-Type"] = "application/text"
        r = requests.post(url, headers=headers, data=sql)
        if r.status_code == 401:
            refresh_access_token()
            r = requests.post(url, headers=headers, data=sql)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/quickbooks/customers")
def quickbooks_customers():
    data = qb_query("SELECT * FROM Customer")
    return {"customers": data.get("QueryResponse", {}).get("Customer", [])}

@app.get("/quickbooks/invoices")
def quickbooks_invoices():
    data = qb_query("SELECT * FROM Invoice")
    return {"invoices": data.get("QueryResponse", {}).get("Invoice", [])}

@app.get("/quickbooks/accounts")
def quickbooks_accounts():
    data = qb_query("SELECT * FROM Account")
    return {"accounts": data.get("QueryResponse", {}).get("Account", [])}

@app.post("/quickbooks/expenses")
async def quickbooks_expenses(request: Request):
    try:
        body = await request.json()
        vendor = body.get("Vendor")
        amount = body.get("Amount")
        category = body.get("Category")

        tokens = load_tokens()
        realm_id = tokens["realm_id"]
        url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/purchase"

        payload = {
            "TxnDate": str(datetime.date.today()),
            "PrivateNote": category,
            "TotalAmt": float(amount),
            "EntityRef": {"type": "Vendor", "name": vendor},
        }

        r = requests.post(url, headers=get_auth_header(), json=payload)
        if r.status_code == 401:
            refresh_access_token()
            r = requests.post(url, headers=get_auth_header(), json=payload)

        if r.status_code == 200:
            txn_id = r.json().get("Purchase", {}).get("Id", "N/A")
            append_to_google_sheet(vendor, amount, category, txn_id)
            return {"status": "Expense added successfully", "txn_id": txn_id}
        else:
            return {"error": f"QuickBooks API failed: {r.text}"}
    except Exception as e:
        return {"error": str(e)}
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "https://symbols-superb-icons-exhibitions.trycloudflare.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
