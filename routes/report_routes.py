from fastapi import APIRouter
from fastapi.responses import FileResponse
from models.storage import get_receipts
import csv
import os
from datetime import datetime
import re

router = APIRouter(prefix="/reports", tags=["Reports"])


def safe_amount(value):
    try:
        return float(value)
    except:
        return 0.0

@router.get("/tax-report")
def generate_tax_report():
    receipts = get_receipts()

    totals = {}

    for r in receipts:
        deduction = r.get("deduction_type", "Other")
        amount = safe_amount(r.get("amount", 0))

        totals[deduction] = totals.get(deduction, 0) + amount

    os.makedirs("uploads", exist_ok=True)

    filename = f"tax_report_{int(datetime.utcnow().timestamp())}.csv"
    filepath = os.path.join("uploads", filename)

    with open(filepath, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Deduction Type", "Total Amount"])

        for k, v in totals.items():
            writer.writerow([k, f"{v:.2f}"])

        writer.writerow([])
        writer.writerow(["TOTAL", f"{sum(totals.values()):.2f}"])

    return FileResponse(filepath, filename=filename, media_type="text/csv")