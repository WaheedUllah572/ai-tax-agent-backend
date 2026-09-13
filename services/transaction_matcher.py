from models.storage import (
    get_receipts,
    get_transactions,
    save_transactions,
    save_receipts,
)
from datetime import datetime
import re


def clean_amount(a):
    try:
        if isinstance(a, str):
            a = a.replace(",", "")
            a = re.sub(r"[A-Za-zRs$€£ ]", "", a)
        return float(a)
    except Exception:
        return 0.0


def normalize_vendor(v):
    if not v:
        return ""
    return v.lower().strip()


def parse_date(date_str):
    if not date_str:
        return None

    date_str = date_str.replace(",", "").strip()

    formats = [
        "%Y-%m-%d",
        "%d %B %Y",
        "%B %d %Y",
        "%d-%m-%Y",
        "%d %m %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue

    return None


def match_transactions(user_id):
    """
    Match transactions ONLY against receipts belonging to the
    authenticated user.

    This function intentionally keeps the shared storage format
    but isolates the matching operation by user_id.
    """

    user_id = str(user_id)

    all_receipts = get_receipts()
    all_transactions = get_transactions()

    if not isinstance(all_receipts, list):
        all_receipts = []

    if not isinstance(all_transactions, list):
        all_transactions = []

    # IMPORTANT:
    # Never allow records from another user into the matching operation.
    user_transactions = [
        tx for tx in all_transactions
        if str(tx.get("user_id", "")) == user_id
    ]

    user_receipts = [
        receipt for receipt in all_receipts
        if str(receipt.get("user_id", "")) == user_id
    ]

    for tx in user_transactions:
        if tx.get("matched"):
            continue

        tx_amount = clean_amount(tx.get("amount"))
        tx_date = parse_date(tx.get("date"))
        tx_vendor = normalize_vendor(tx.get("vendor"))

        print("\n--- Checking Transaction ---")
        print("TX Vendor:", tx_vendor)
        print("TX Amount:", tx_amount)
        print("TX Date:", tx_date)

        for receipt in user_receipts:
            if receipt.get("matched"):
                continue

            receipt_amount = clean_amount(receipt.get("amount"))
            receipt_date = parse_date(receipt.get("date"))
            receipt_vendor = normalize_vendor(receipt.get("vendor"))

            print("   Receipt Vendor:", receipt_vendor)
            print("   Receipt Amount:", receipt_amount)
            print("   Receipt Date:", receipt_date)

            amount_match = abs(tx_amount - receipt_amount) < 1
            vendor_match = tx_vendor == receipt_vendor

            date_match = False

            if tx_date and receipt_date:
                diff = abs((tx_date - receipt_date).days)

                if diff <= 1:
                    date_match = True

            print("   Amount Match:", amount_match)
            print("   Vendor Match:", vendor_match)
            print("   Date Match:", date_match)

            if amount_match and vendor_match and date_match:
                print(">>> MATCH FOUND <<<")

                tx["matched"] = True
                tx["receipt_id"] = receipt["id"]

                receipt["matched"] = True

                break

    # Update ONLY the authenticated user's transactions in the
    # complete transaction collection.
    transaction_updates = {
        tx["id"]: tx
        for tx in user_transactions
        if tx.get("id")
    }

    for tx in all_transactions:
        tx_id = tx.get("id")

        if tx_id in transaction_updates:
            tx.update(transaction_updates[tx_id])

    save_transactions(all_transactions)

    # Update ONLY the authenticated user's receipts.
    receipt_updates = {
        receipt["id"]: receipt
        for receipt in user_receipts
        if receipt.get("id")
    }

    receipts_to_save = []

    for receipt in all_receipts:
        receipt_id = receipt.get("id")

        if receipt_id in receipt_updates:
            receipts_to_save.append(receipt)

    if receipts_to_save:
        save_receipts(receipts_to_save)

    return user_transactions