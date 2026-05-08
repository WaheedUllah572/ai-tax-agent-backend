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
# IMAGE PREPROCESSING
# =========================================
def preprocess_image(file_bytes):
    try:

        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        img_np = np.array(image)

        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        # LIGHT preprocessing only
        # heavy thresholding was breaking clean receipts

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
# OCR EXTRACTION
# =========================================
def extract_text_from_image(file_bytes):

    try:

        processed = preprocess_image(file_bytes)

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
# STRONG AMOUNT DETECTION
# =========================================
def extract_amount_from_text(text):

    priority_patterns = [

        # TOTAL
        r"grand total\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"total\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"amount\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"paid\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"subtotal\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"fare\s*[: ]\s*\$?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        # PKR
        r"pkr\.?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        r"rs\.?\s?(\d+(?:,\d{3})*(?:\.\d{2})?)",

        # USD
        r"\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)"
    ]

    for pattern in priority_patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        if matches:

            try:

                value = matches[0]

                cleaned = (
                    str(value)
                    .replace(",", "")
                    .strip()
                )

                amount = float(cleaned)

                if amount > 0:
                    return amount

            except:
                pass

    return 0.0


# =========================================
# CURRENCY DETECTION
# =========================================
def detect_currency(text):

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
# AI METADATA EXTRACTION
# =========================================
def ai_extract_metadata(file_bytes):

    try:

        base64_image = base64.b64encode(
            file_bytes
        ).decode("utf-8")

        response = client.chat.completions.create(

            model="gpt-4o",

            messages=[

                {
                    "role": "system",
                    "content": """
You are a receipt analyzer.

Extract ONLY:
- vendor
- date
- category
- document_type

STRICT RULES:
- No explanations
- Return ONLY valid JSON
- Do NOT include markdown

JSON format:

{
  "vendor": "",
  "date": "",
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
                            "text": "Analyze this receipt."
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

            max_tokens=300
        )

        content = response.choices[0].message.content

        content = re.sub(
            r"```json|```",
            "",
            content
        ).strip()

        return json.loads(content)

    except Exception as e:

        print("AI ERROR:", e)

        return {}


# =========================================
# SMART CATEGORY
# =========================================
def smart_category(vendor, text):

    combined = f"{vendor} {text}".lower()

    if "uber" in combined or "lyft" in combined:
        return "Transportation"

    if (
        "bakery" in combined
        or "restaurant" in combined
        or "food" in combined
    ):
        return "Meals"

    if (
        "electric" in combined
        or "utility" in combined
        or "internet" in combined
    ):
        return "Utilities"

    if (
        "hotel" in combined
        or "flight" in combined
        or "travel" in combined
    ):
        return "Travel"

    if (
        "store" in combined
        or "mart" in combined
        or "shop" in combined
    ):
        return "General Expense"

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
# MAIN FUNCTION
# =========================================
async def analyze_receipt_image(file_bytes: bytes):

    try:

        # =================================
        # STEP 1 OCR
        # =================================
        raw_text = extract_text_from_image(
            file_bytes
        )

        print("\n========== OCR TEXT ==========")
        print(raw_text)

        # =================================
        # STEP 2 AMOUNT
        # =================================
        amount = extract_amount_from_text(
            raw_text
        )

        print("EXTRACTED AMOUNT:", amount)

        # =================================
        # STEP 3 CURRENCY
        # =================================
        currency = detect_currency(raw_text)

        print("CURRENCY:", currency)

        # =================================
        # STEP 4 AI METADATA
        # =================================
        ai_data = ai_extract_metadata(
            file_bytes
        )

        vendor = (
            ai_data.get("vendor")
            or "unknown"
        ).lower().strip()

        category = (
            ai_data.get("category")
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
                ai_data.get("date")
            ),

            "amount": amount,

            "currency": currency,

            "category": category,

            "document_type": (
                ai_data.get("document_type")
                or "Receipt"
            ),

            "deduction_type": category
        }

        result["ai_confidence"] = calculate_confidence(
            result
        )

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