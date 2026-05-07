import os
import json
import base64
import re
from datetime import datetime
from openai import OpenAI
import pytesseract
from PIL import Image
import io

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =============================
# OCR STEP (PERMANENT FIX)
# =============================
def extract_text_from_image(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        return text.lower()
    except:
        return ""


# =============================
# STRONG AMOUNT DETECTION
# =============================
def extract_amount_from_text(text):
    matches = re.findall(r"(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)", text)

    if not matches:
        return 0.0

    values = []
    for m in matches:
        cleaned = m.replace(",", "")
        try:
            values.append(float(cleaned))
        except:
            pass

    return max(values) if values else 0.0


# =============================
# STRONG CURRENCY DETECTION
# =============================
def detect_currency(text):
    if "pkr" in text or "rs" in text or "₨" in text:
        return "PKR"
    if "$" in text or "usd" in text:
        return "USD"
    return "UNKNOWN"


def normalize_date(date_str):
    if not date_str:
        return ""

    formats = [
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%d/%m/%Y",
        "%d-%m-%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue

    return ""


def calculate_confidence(data):
    score = 0
    if data.get("vendor"): score += 1
    if data.get("amount", 0) > 0: score += 1
    if data.get("date"): score += 1

    return ["low", "medium", "high"][score - 1] if score > 0 else "low"


# =============================
# MAIN FUNCTION (FIXED)
# =============================
async def analyze_receipt_image(file_bytes: bytes) -> dict:
    try:
        # 🔥 STEP 1: OCR FIRST
        raw_text = extract_text_from_image(file_bytes)

        # 🔥 STEP 2: RULE-BASED EXTRACTION
        amount = extract_amount_from_text(raw_text)
        currency = detect_currency(raw_text)

        # 🔥 STEP 3: AI ONLY FOR METADATA
        base64_image = base64.b64encode(file_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
Extract vendor, date, category.

Return JSON:
{
  "vendor": "",
  "date": "",
  "category": "",
  "document_type": "",
  "deduction_type": ""
}
"""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze receipt."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                    ],
                },
            ],
            max_tokens=300,
        )

        content = response.choices[0].message.content
        content = re.sub(r"```json|```", "", content).strip()

        data = json.loads(content)

        result = {
            "vendor": (data.get("vendor") or "unknown").lower(),
            "date": normalize_date(data.get("date")),
            "amount": amount,
            "currency": currency,
            "category": data.get("category") or "Uncategorized",
            "document_type": data.get("document_type") or "Unknown",
            "deduction_type": data.get("deduction_type") or "Uncategorized",
        }

        result["ai_confidence"] = calculate_confidence(result)

        return result

    except Exception as e:
        print("ERROR:", e)

        return {
            "vendor": "unknown",
            "date": "",
            "amount": 0.0,
            "currency": "UNKNOWN",
            "category": "Uncategorized",
            "document_type": "Unknown",
            "deduction_type": "Uncategorized",
            "ai_confidence": "low"
        }