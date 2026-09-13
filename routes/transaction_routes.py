from fastapi import APIRouter, Depends
from datetime import datetime
import uuid

from dependencies.auth_dependency import get_current_user
from models.storage import get_transactions, save_transactions
from services.transaction_matcher import match_transactions


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("/add")
async def add_transaction(
    data: dict,
    current_user=Depends(get_current_user)
):
    user_id = str(current_user.id)

    transactions = get_transactions()

    if not isinstance(transactions, list):
        transactions = []

    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
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

    return {
        "success": True,
        "transaction": transaction
    }


@router.get("/all")
async def get_all_transactions(
    current_user=Depends(get_current_user)
):
    user_id = str(current_user.id)

    transactions = get_transactions()

    if not isinstance(transactions, list):
        return []

    # Return ONLY the authenticated user's transactions
    return [
        tx for tx in transactions
        if str(tx.get("user_id", "")) == user_id
    ]


@router.post("/match")
async def match_all_transactions(
    current_user=Depends(get_current_user)
):
    user_id = str(current_user.id)

    result = match_transactions(user_id)

    return {
        "success": True,
        "transactions": result
    }