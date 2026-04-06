from models.storage import get_receipts, get_transactions, save_transactions, save_receipts
from datetime import datetime
import re


def clean_amount(a):
    try:
        if isinstance(a, str):
            a = a.replace(",", "")
            a = re.sub(r"[A-Za-zRs$€£ ]", "", a)
        return float(a)
    except:
        return 0.0


def normalize_vendor(v):
    if not v:
        return ""
    return v.lower().strip()


def parse_date(date_str):
    if not date_str:
        return None

    # Remove commas
    date_str = date_str.replace(",", "").strip()

    formats = [
        "%Y-%m-%d",
        "%d %B %Y",
        "%B %d %Y",
        "%d-%m-%Y",
        "%d %m %Y",
        "%d %b %Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue

    return None


def match_transactions():
    receipts = get_receipts()
    transactions = get_transactions()

    for tx in transactions:
        if tx.get("matched"):
            continue

        tx_amount = clean_amount(tx.get("amount"))
        tx_date = parse_date(tx.get("date"))
        tx_vendor = normalize_vendor(tx.get("vendor"))

        print("\n--- Checking Transaction ---")
        print("TX Vendor:", tx_vendor)
        print("TX Amount:", tx_amount)
        print("TX Date:", tx_date)

        for r in receipts:
            if r.get("matched"):
                continue

            r_amount = clean_amount(r.get("amount"))
            r_date = parse_date(r.get("date"))
            r_vendor = normalize_vendor(r.get("vendor"))

            print("   Receipt Vendor:", r_vendor)
            print("   Receipt Amount:", r_amount)
            print("   Receipt Date:", r_date)

            amount_match = abs(tx_amount - r_amount) < 1
            vendor_match = tx_vendor == r_vendor

            date_match = False
            if tx_date and r_date:
                diff = abs((tx_date - r_date).days)
                if diff <= 1:
                    date_match = True

            print("   Amount Match:", amount_match)
            print("   Vendor Match:", vendor_match)
            print("   Date Match:", date_match)

            if amount_match and vendor_match and date_match:
                print(">>> MATCH FOUND <<<")
                tx["matched"] = True
                tx["receipt_id"] = r["id"]
                r["matched"] = True
                break

    save_transactions(transactions)
    save_receipts(receipts)

    return transactions