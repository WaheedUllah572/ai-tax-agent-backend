from fastapi import APIRouter
from fastapi.responses import FileResponse
from models.storage import get_receipts
import csv
import os
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/tax-report")
def generate_tax_report():
    receipts = get_receipts()

    totals = {}

    for r in receipts:
        deduction = r.get("deduction_type", "Other")
        try:
            amount = float(str(r.get("amount", 0)).replace("$", "").replace(",", ""))
        except:
            amount = 0.0

        totals[deduction] = totals.get(deduction, 0) + amount

    # Ensure uploads folder exists
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