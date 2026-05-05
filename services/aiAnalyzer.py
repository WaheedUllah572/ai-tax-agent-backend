import os
import json
import base64
import re
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def normalize_amount(amount):
    try:
        original = str(amount)

        if not original:
            return 0.0

        # Remove currency symbols and text
        cleaned = re.sub(r"[^\d.,]", "", original)

        if cleaned == "":
            return 0.0

        # Handle comma (thousands separator)
        if "," in cleaned:
            cleaned = cleaned.replace(",", "")

        # Handle dot confusion (OCR issues like 1.250 vs 1250)
        if "." in cleaned:
            parts = cleaned.split(".")
            if len(parts[-1]) == 3 and len(parts) > 1:
                cleaned = cleaned.replace(".", "")

        value = float(cleaned)

        # OCR decimal shift correction
        digits = len(re.sub(r"[^\d]", "", original))

        if value < 10 and digits >= 4:
            value = value * 1000
        elif value < 100 and digits >= 4:
            value = value * 10

        return value

    except:
        return 0.0


def normalize_date(date_str):
    if not date_str:
        return ""

    date_str = date_str.replace(",", "").strip()

    formats = [
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d-%m-%Y",
        "%d/%m/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue

    return date_str


def calculate_confidence(data: dict) -> str:
    score = 0

    if data.get("vendor"):
        score += 1

    amount = normalize_amount(data.get("amount", "0"))
    if amount > 0:
        score += 1

    if data.get("date"):
        score += 1

    if score == 3:
        return "high"
    elif score == 2:
        return "medium"
    else:
        return "low"


async def analyze_receipt_image(file_bytes: bytes) -> dict:
    try:
        base64_image = base64.b64encode(file_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
You are a professional financial document analyzer.

Extract structured data from receipts, invoices, or tax documents.

IMPORTANT:
- Amount must be numeric only (example: 1250.50)
- Do NOT include currency symbols like Rs, $, etc.

Return STRICT JSON:

{
  "vendor": "",
  "date": "",
  "amount": "",
  "category": "",
  "document_type": "",
  "deduction_type": ""
}
"""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this financial document."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                    ],
                },
            ],
            max_tokens=500,
        )

        content = response.choices[0].message.content

        # CLEAN RESPONSE (VERY IMPORTANT)
        content = content.strip()
        content = re.sub(r"```json", "", content)
        content = re.sub(r"```", "", content)
        content = content.strip()

        data = json.loads(content)

        # NORMALIZE
        data["amount"] = normalize_amount(data.get("amount"))
        data["date"] = normalize_date(data.get("date"))
        data["vendor"] = (data.get("vendor") or "").lower().strip()

        # CONFIDENCE
        data["ai_confidence"] = calculate_confidence(data)

        return data

    except Exception as e:
        print("OPENAI ERROR:", e)
        return {
            "vendor": "processing error",
            "date": "",
            "amount": 0.0,
            "category": "Uncategorized",
            "document_type": "Unknown",
            "deduction_type": "Uncategorized",
            "ai_confidence": "low"
        }