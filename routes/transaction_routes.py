from fastapi import APIRouter
from datetime import datetime
import uuid

from models.storage import get_transactions, save_transactions
from services.transaction_matcher import match_transactions

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/add")
async def add_transaction(data: dict):
    transactions = get_transactions()

    transaction = {
        "id": str(uuid.uuid4()),
        "date": data.get("date"),
        "vendor": data.get("vendor"),
        "amount": data.get("amount"),
        "source": data.get("source", "bank"),
        "matched": False,
        "receipt_id": None,
        "created_at": datetime.utcnow().isoformat()
    }

    transactions.append(transaction)
    save_transactions(transactions)

    return {"success": True, "transaction": transaction}


@router.get("/all")
async def get_all_transactions():
    return get_transactions()


@router.post("/match")
async def match_all_transactions():
    result = match_transactions()
    return {"success": True, "transactions": result}