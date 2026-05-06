import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

RECEIPT_FILE = os.path.join(BASE_DIR, "receipts.json")
MILEAGE_FILE = os.path.join(BASE_DIR, "mileage.json")
TRANSACTION_FILE = os.path.join(BASE_DIR, "transactions.json")


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


def get_receipts():
    data = load_data(RECEIPT_FILE)
    return data


def save_receipts(data):
    save_data(RECEIPT_FILE, data)


def get_mileage():
    return load_data(MILEAGE_FILE)


def save_mileage(data):
    save_data(MILEAGE_FILE, data)


def get_transactions():
    return load_data(TRANSACTION_FILE)


def save_transactions(data):
    save_data(TRANSACTION_FILE, data)