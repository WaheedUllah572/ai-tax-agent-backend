from fastapi import APIRouter
from fastapi import Depends
from dependencies.auth_dependency import get_current_user
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
def accountant_dashboard(
    current_user=Depends(get_current_user)
):

    receipts = get_receipts()
    transactions = get_transactions()
    mileage = get_mileage()

    total_receipts = len(receipts)
    total_transactions = len(transactions)
    total_mileage = len(mileage)

    total_expenses = 0

    approved = 0
    pending = 0
    rejected = 0
    reviewed = 0

    deductible_total = 0
    non_deductible_total = 0

    vendors = {}

    for r in receipts:

        try:
            amount = float(r.get("amount", 0))
        except:
            amount = 0

        total_expenses += amount

        status = r.get("status", "Pending")

        if status == "Locked":
            approved += 1
        elif status == "Rejected":
            rejected += 1
        elif status == "Reviewed":
            reviewed += 1
        else:
            pending += 1

        deductible_total += float(
            r.get("deductible_amount", 0)
        )

        non_deductible_total += (
            amount - float(r.get("deductible_amount", 0))
        )

        vendor = r.get("vendor", "Unknown")

        vendors[vendor] = vendors.get(vendor, 0) + amount

    top_vendors = sorted(
        vendors.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {

        "total_receipts": total_receipts,
        "total_transactions": total_transactions,
        "total_mileage_logs": total_mileage,
        "total_expenses": round(total_expenses,2),

        "approved": approved,
        "pending": pending,
        "reviewed": reviewed,
        "rejected": rejected,

        "deductible_total": round(deductible_total,2),
        "non_deductible_total": round(non_deductible_total,2),

        "top_vendors": top_vendors,

        "receipts": receipts,
        "transactions": transactions,
        "mileage": mileage,
    }


    return []

    users = load_users()

    clients = []

    for user in users:

        if user.get("role") == "owner":

            clients.append({
                "name": user.get("name"),
                "email": user.get("email")
            })

    return clients

    return {
        "message": "Accountant client management will be available in the next version."
    }

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
    
