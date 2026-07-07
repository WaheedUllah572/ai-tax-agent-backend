from fastapi import APIRouter
from models.storage import (
    get_receipts,
    get_transactions,
    get_mileage,
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