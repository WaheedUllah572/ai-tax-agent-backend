from fastapi import APIRouter
from fastapi.responses import FileResponse
from models.storage import get_receipts
import csv
import os
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["Reports"])


def safe_amount(value):

    try:
        return float(value)
    except:
        return 0.0


# =====================================
# EXPORT TAX REPORT
# =====================================
@router.get("/tax-report")
def generate_tax_report():

    receipts = get_receipts()

    totals = {}

    for r in receipts:

        deduction = r.get("deduction_type", "Other")

        amount = safe_amount(
            r.get("usd_amount", r.get("amount", 0))
        )

        totals[deduction] = (
            totals.get(deduction, 0)
            + amount
        )

    os.makedirs("uploads", exist_ok=True)

    filename = (
        f"tax_report_{int(datetime.utcnow().timestamp())}.csv"
    )

    filepath = os.path.join(
        "uploads",
        filename
    )

    with open(filepath, "w", newline="") as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "Deduction Type",
            "USD Total Amount"
        ])

        for k, v in totals.items():

            writer.writerow([
                k,
                f"{v:.2f}"
            ])

        writer.writerow([])

        writer.writerow([
            "TOTAL USD",
            f"{sum(totals.values()):.2f}"
        ])

    return FileResponse(
        filepath,
        filename=filename,
        media_type="text/csv"
    )


# =====================================
# DASHBOARD ANALYTICS
# =====================================
@router.get("/analytics")
def dashboard_analytics():

    receipts = get_receipts()

    total_receipts = len(receipts)

    total_spending = 0

    vendor_map = {}

    category_map = {}

    monthly_map = {
        "Jan": 0,
        "Feb": 0,
        "Mar": 0,
        "Apr": 0,
        "May": 0,
        "Jun": 0,
        "Jul": 0,
        "Aug": 0,
        "Sep": 0,
        "Oct": 0,
        "Nov": 0,
        "Dec": 0
    }

    for r in receipts:

        # ✅ FIXED
        amount = safe_amount(
            r.get("usd_amount", r.get("amount", 0))
        )

        total_spending += amount

        vendor = (
            r.get("vendor")
            or "Unknown"
        )

        vendor_map[vendor] = (
            vendor_map.get(vendor, 0)
            + amount
        )

        category = (
            r.get("category")
            or "Other"
        )

        category_map[category] = (
            category_map.get(category, 0)
            + amount
        )

        try:

            date = r.get("date")

            if date:

                month_index = int(date.split("-")[1])

                months = list(monthly_map.keys())

                month_name = months[month_index - 1]

                monthly_map[month_name] += amount

        except:
            pass

    top_vendor = "—"
    needs_review_count = len([
        r for r in receipts
        if r.get("needs_review") is True
    ])

    if vendor_map:

        top_vendor = max(
            vendor_map,
            key=vendor_map.get
        )

    return {

        "total_receipts": total_receipts,

        "total_spending": round(
            total_spending,
            2
        ),

        "top_vendor": top_vendor,

        "monthly_data": monthly_map,

        "category_data": category_map,

        "vendor_data": vendor_map,

        "needs_review_count": needs_review_count
    }