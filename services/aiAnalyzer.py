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
# IMAGE PREPROCESSING (MAJOR FIX)
# =========================================
def preprocess_image(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        img_np = np.array(image)

        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        # sharpen
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # threshold
        processed = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        return processed

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

        text = pytesseract.image_to_string(processed)

        return text.lower()

    except Exception as e:
        print("OCR ERROR:", e)
        return ""


# =========================================
# STRONG AMOUNT DETECTION
# =========================================
def extract_amount_from_text(text):

    patterns = [
        r"\$\s?(\d+[.,]?\d*)",
        r"pkr\.?\s?(\d+[.,]?\d*)",
        r"rs\.?\s?(\d+[.,]?\d*)",
        r"total\s?[: ]\s?(\d+[.,]?\d*)",
        r"amount\s?[: ]\s?(\d+[.,]?\d*)",
        r"(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)",
        r"(\d+\.\d{2})"
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for m in matches:
            try:
                cleaned = str(m).replace(",", "").strip()

                value = float(cleaned)

                # ignore tiny numbers
                if value > 1:
                    values.append(value)

            except:
                pass

    if not values:
        return 0.0

    return max(values)


# =========================================
# CURRENCY DETECTION
# =========================================
def detect_currency(text):

    text = text.lower()

    if "pkr" in text or "rs." in text or "₨" in text:
        return "PKR"

    if "$" in text or "usd" in text:
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
        "%d-%m-%Y"
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

        base64_image = base64.b64encode(file_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
Extract:
- vendor
- date
- category
- document_type

Return ONLY JSON:

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
                            "text": "Analyze receipt"
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

        content = re.sub(r"```json|```", "", content).strip()

        return json.loads(content)

    except Exception as e:
        print("AI ERROR:", e)
        return {}


# =========================================
# CATEGORY MAPPING
# =========================================
def smart_category(vendor, text):

    combined = f"{vendor} {text}".lower()

    if "uber" in combined or "lyft" in combined:
        return "Transportation"

    if "bakery" in combined or "restaurant" in combined:
        return "Meals"

    if "electric" in combined or "utility" in combined:
        return "Utilities"

    if "hotel" in combined or "flight" in combined:
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
# MAIN FUNCTION
# =========================================
async def analyze_receipt_image(file_bytes: bytes):

    try:

        # STEP 1 OCR
        raw_text = extract_text_from_image(file_bytes)

        # STEP 2 AMOUNT
        amount = extract_amount_from_text(raw_text)

        # STEP 3 CURRENCY
        currency = detect_currency(raw_text)

        # STEP 4 AI
        ai_data = ai_extract_metadata(file_bytes)

        vendor = (
            ai_data.get("vendor")
            or "unknown"
        ).lower().strip()

        category = (
            ai_data.get("category")
            or smart_category(vendor, raw_text)
        )

        result = {
            "vendor": vendor,
            "date": normalize_date(
                ai_data.get("date")
            ),
            "amount": amount,
            "currency": currency,
            "category": category,
            "document_type": ai_data.get(
                "document_type"
            ) or "Receipt",
            "deduction_type": category
        }

        result["ai_confidence"] = calculate_confidence(result)

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