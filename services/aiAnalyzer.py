import os
import json
import base64
import re
from datetime import datetime
from openai import OpenAI

import pytesseract
from PIL import Image
import io
import cv2
import numpy as np

from models.storage import (
    get_vendor_rules,
    save_vendor_rules
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================================
# LIGHT OCR FALLBACK ONLY
# =========================================
def preprocess_image(file_bytes):

    try:

        image = Image.open(
            io.BytesIO(file_bytes)
        ).convert("RGB")

        img_np = np.array(image)

        gray = cv2.cvtColor(
            img_np,
            cv2.COLOR_RGB2GRAY
        )

        gray = cv2.resize(
            gray,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        return gray

    except Exception as e:

        print("PREPROCESS ERROR:", e)

        return None


# =========================================
# OCR FALLBACK
# =========================================
def extract_text_from_image(file_bytes):

    try:

        processed = preprocess_image(
            file_bytes
        )

        if processed is None:
            return ""

        text = pytesseract.image_to_string(
            processed,
            config="--psm 6"
        )

        return text.lower()

    except Exception as e:

        print("OCR ERROR:", e)

        return ""


# =========================================
# BACKUP AMOUNT EXTRACTION
# =========================================
def fallback_extract_amount(text):

    patterns = [

        r"grand total\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"total\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"amount\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"subtotal\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"fare\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"pkr\.?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"rs\.?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"eur\.?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"€\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)"
    ]

    values = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:

            try:

                value = (
                    str(match)
                    .replace(",", "")
                    .strip()
                )

                amount = float(value)

                if amount > 0:
                    values.append(amount)

            except:
                pass

    if values:
        return max(values)

    return 0.0


# =========================================
# BACKUP CURRENCY DETECTION
# =========================================
def fallback_currency(text):

    text = text.lower()

    if (
        "pkr" in text
        or "rs." in text
        or "rs " in text
        or "₨" in text
    ):
        return "PKR"

    if (
        "eur" in text
        or "€" in text
        or "euro" in text
    ):
        return "EUR"

    if (
        "$" in text
        or "usd" in text
        or "uber" in text
    ):
        return "USD"

    return "USD"


# =========================================
# DATE NORMALIZATION
# =========================================
def normalize_date(date_str):

    if not date_str:
        return ""

    date_str = date_str.strip()

    formats = [

        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%B %d %Y",
        "%b %d %Y"
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                date_str,
                fmt
            ).strftime("%Y-%m-%d")

        except:
            pass

    return ""


# =========================================
# SMART CATEGORY FALLBACK
# =========================================
def smart_category(vendor, text):

    combined = f"{vendor} {text}".lower()

    if (
        "uber" in combined
        or "lyft" in combined
    ):
        return "Transportation"

    if (
        "restaurant" in combined
        or "food" in combined
        or "bakery" in combined
    ):
        return "Meals"

    if (
        "utility" in combined
        or "electric" in combined
        or "internet" in combined
    ):
        return "Utilities"

    if (
        "hotel" in combined
        or "flight" in combined
        or "travel" in combined
    ):
        return "Travel"

    return "General Expense"


# =========================================
# VENDOR LEARNING
# =========================================
def learn_vendor(vendor, category, deduction_type):

    if not vendor or vendor == "unknown":
        return

    vendors = get_vendor_rules()

    existing = None

    for v in vendors:

        if v["vendor"] == vendor:
            existing = v
            break

    if existing:

        existing["category"] = category
        existing["deduction_type"] = deduction_type
        existing["times_used"] += 1

    else:

        vendors.append({
            "vendor": vendor,
            "category": category,
            "deduction_type": deduction_type,
            "times_used": 1
        })

    save_vendor_rules(vendors)


def get_vendor_learning(vendor):

    vendors = get_vendor_rules()

    for v in vendors:

        if v["vendor"] == vendor:
            return v

    return None


# =========================================
# CONFIDENCE
# =========================================
def calculate_confidence(data):

    score = 0

    if data.get("vendor"):
        score += 1

    if data.get("amount", 0) > 0:
        score += 1

    if data.get("date"):
        score += 1

    if score == 3:
        return "high"

    if score == 2:
        return "medium"

    return "low"


# =========================================
# MAIN AI FUNCTION
# =========================================
async def analyze_receipt_image(file_bytes: bytes):

    try:

        # =================================
        # OCR BACKUP
        # =================================
        raw_text = extract_text_from_image(
            file_bytes
        )

        print("\n========== OCR TEXT ==========")
        print(raw_text)

        # =================================
        # GPT VISION
        # =================================
        base64_image = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        response = client.chat.completions.create(

            model="gpt-4o",

            response_format={
                "type": "json_object"
            },

            messages=[

                {
                    "role": "system",
                    "content": """
You are an expert receipt extraction AI.

Extract:
- vendor
- date
- final total amount
- currency
- category
- document type

CRITICAL:
- Extract FINAL TOTAL ONLY
- Return amount as numeric value
- Do not include currency symbols in amount
- Return ONLY JSON

JSON FORMAT:

{
  "vendor": "",
  "date": "",
  "amount": 0,
  "currency": "",
  "category": "",
  "document_type": ""
}
"""
                },

                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text": "Extract receipt data accurately."
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],

            max_tokens=500
        )

        content = response.choices[0].message.content

        print("\n========== GPT RESPONSE ==========")
        print(content)

        data = json.loads(content)

        # =================================
        # SAFE AMOUNT PARSING
        # =================================
        raw_amount = str(
            data.get("amount", "0")
        )

        raw_amount = re.sub(
            r"[^\d.]",
            "",
            raw_amount
        )

        try:

            amount = float(raw_amount)

        except:

            amount = 0.0

        # =================================
        # SAFE CURRENCY
        # =================================
        currency = (
            data.get("currency")
            or ""
        ).upper().strip()

        # =================================
        # FALLBACK FIXES
        # =================================
        if amount <= 0.0:

            print("USING OCR FALLBACK")

            amount = fallback_extract_amount(
                raw_text
            )

        if not currency:

            currency = fallback_currency(
                raw_text
            )

        # =================================
        # SAFE VENDOR
        # =================================
        vendor = (
            data.get("vendor")
            or "unknown"
        ).lower().strip()

        # =================================
        # VENDOR LEARNING
        # =================================
        vendor_learning = get_vendor_learning(
            vendor
        )

        if vendor_learning:

            category = vendor_learning[
                "category"
            ]

            learned_deduction = (
                vendor_learning[
                    "deduction_type"
                ]
            )

            learned_vendor = True

        else:

            category = (
                data.get("category")
                or smart_category(
                    vendor,
                    raw_text
                )
            )

            learned_deduction = category

            learned_vendor = False

            learn_vendor(
                vendor,
                category,
                learned_deduction
            )

        # =================================
        # FINAL RESULT
        # =================================
        result = {

            "vendor": vendor,

            "date": normalize_date(
                data.get("date")
            ),

            "amount": amount,

            "currency": currency,

            "category": category,

            "document_type": (
                data.get("document_type")
                or "Receipt"
            ),

            "deduction_type":
                learned_deduction,

            "vendor_learned":
                learned_vendor
        }
        confidence = calculate_confidence(result)

        result["ai_confidence"] = confidence

        # =================================
        # NEEDS REVIEW LOGIC
        # =================================
        result["needs_review"] = (
            confidence != "high"
        )
        print("\n========== FINAL RESULT ==========")
        print(result)

        return result

    except Exception as e:

        print("FINAL ERROR:", e)

        return {

            "vendor": "unknown",

            "date": "",

            "amount": 0.0,

            "currency": "USD",

            "category": "General Expense",

            "document_type": "Receipt",

            "deduction_type":
                "General Expense",

            "vendor_learned": False,

            "ai_confidence": "low"
        }