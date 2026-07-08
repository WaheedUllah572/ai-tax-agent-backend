from fastapi import APIRouter
import json
USERS_DB = "users.json"
from models.storage import (
    get_receipts,
    get_transactions,
    get_mileage,
    get_clients,
    save_clients,
)

router = APIRouter(
    prefix="/accountant",
    tags=["Accountant"]
)


@router.get("/dashboard")
def accountant_dashboard():

    receipts = get_receipts()
    transactions = get_transactions()
    mileage = get_mileage()

    total_receipts = len(receipts)
    total_transactions = len(transactions)
    total_mileage = len(mileage)

    total_expenses = 0

    for r in receipts:
        try:
            total_expenses += float(r.get("amount", 0))
        except:
            pass

    return {
        "total_receipts": total_receipts,
        "total_transactions": total_transactions,
        "total_mileage_logs": total_mileage,
        "total_expenses": round(total_expenses, 2),
        "receipts": receipts,
        "transactions": transactions,
        "mileage": mileage,
    }


@router.get("/clients")
def get_all_clients():

    users = load_users()

    clients = []

    for user in users:

        if user.get("role") == "owner":

            clients.append({
                "name": user.get("name"),
                "email": user.get("email")
            })

    return clients

@router.get("/client/{email}")
def get_client(email: str):

    users = load_users()

    user = next(
        (u for u in users if u["email"] == email),
        None,
    )

    if not user:
        return {"error": "Client not found"}

    receipts = get_receipts()
    transactions = get_transactions()
    mileage = get_mileage()

    return {
        "client": user,
        "receipts": receipts,
        "transactions": transactions,
        "mileage": mileage,
    }
    
def load_users():
    try:
        with open(USERS_DB, "r") as f:
            return json.load(f)
    except:
        return []