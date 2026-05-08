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

        r"\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)"
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        if matches:

            try:

                value = matches[0]

                value = (
                    str(value)
                    .replace(",", "")
                    .strip()
                )

                amount = float(value)

                if amount > 0:
                    return amount

            except:
                pass

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

CRITICAL RULES:
- Extract FINAL TOTAL ONLY
- Never guess
- Never return 0 if amount exists
- Uber receipts contain TOTAL at top
- Return amount as numeric value
- Return ONLY JSON

JSON format:

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
        # AI PRIMARY EXTRACTION
        # =================================
        amount = float(
            data.get("amount", 0)
        )

        currency = (
            data.get("currency")
            or ""
        ).upper()

        # =================================
        # FALLBACK FIXES
        # =================================
        if amount <= 0:

            print("USING OCR FALLBACK")

            amount = fallback_extract_amount(
                raw_text
            )

        if not currency:

            currency = fallback_currency(
                raw_text
            )

        vendor = (
            data.get("vendor")
            or "unknown"
        ).lower().strip()

        category = (
            data.get("category")
            or smart_category(
                vendor,
                raw_text
            )
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

            "deduction_type": category
        }

        result["ai_confidence"] = calculate_confidence(
            result
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

            "deduction_type": "General Expense",

            "ai_confidence": "low"
        }