import json
import os

from database import supabase, supabase_admin

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CLIENT_FILE = os.path.join(BASE_DIR, "clients.json")
RECEIPT_FILE = os.path.join(BASE_DIR, "receipts.json")
MILEAGE_FILE = os.path.join(BASE_DIR, "mileage.json")
TRANSACTION_FILE = os.path.join(BASE_DIR, "transactions.json")

# ✅ NEW
VENDOR_FILE = os.path.join(BASE_DIR, "vendors.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


def load_data(file_path):

    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r") as f:
            return json.load(f)

    except:
        return []


def save_data(file_path, data):

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


# =====================================
# RECEIPTS
# =====================================
def get_receipts():

    response = (
        supabase_admin
        .table("receipts")
        .select("*")
        .execute()
    )

    return response.data


def save_receipts(data):

    supabase_admin.table("receipts").delete().neq(
        "id",
        "00000000-0000-0000-0000-000000000000"
    ).execute()

    if data:
        supabase_admin.table("receipts").insert(data).execute()


# =====================================
# MILEAGE
# =====================================
def get_mileage():
    return load_data(MILEAGE_FILE)


def save_mileage(data):
    save_data(MILEAGE_FILE, data)


# =====================================
# TRANSACTIONS
# =====================================
def get_transactions():
    return load_data(TRANSACTION_FILE)


def save_transactions(data):
    save_data(TRANSACTION_FILE, data)


# =====================================
# ✅ VENDOR LEARNING
# =====================================
def get_vendor_rules():
    return load_data(VENDOR_FILE)


def save_vendor_rules(data):
    save_data(VENDOR_FILE, data)


# =====================================
# ✅ NEW: LEARN FROM USER CORRECTIONS
# =====================================
def save_vendor_correction(
    vendor,
    category,
    deduction_type
):

    if not vendor:
        return

    vendor = vendor.lower().strip()

    vendors = get_vendor_rules()

    existing = None

    for v in vendors:

        if v["vendor"] == vendor:
            existing = v
            break

    if existing:

        existing["category"] = category
        existing["deduction_type"] = deduction_type

        existing["times_used"] = (
            existing.get("times_used", 0) + 1
        )

        existing["manually_corrected"] = True

    else:

        vendors.append({

            "vendor": vendor,

            "category": category,

            "deduction_type": deduction_type,

            "times_used": 1,

            "manually_corrected": True
        })

    save_vendor_rules(vendors)


# =====================================
# SETTINGS
# =====================================

def get_settings():

    data = load_data(SETTINGS_FILE)

    if not data:
        return {
    "jurisdiction": "US",
    "country": "United States",
    "onboarding_completed": False,
    "business_name": "",
    "business_type": "",
}

    return data


def save_settings(data):

    save_data(
        SETTINGS_FILE,
        data
    )

    # =====================================
# CLIENTS
# =====================================

def get_clients():
    return load_data(CLIENT_FILE)


def save_clients(data):
    save_data(CLIENT_FILE, data)