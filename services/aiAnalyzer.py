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

        if isinstance(amount, str):
            # Keep digits and separators
            cleaned = re.sub(r"[^\d.,]", "", amount)

            # Case 1: has comma → normal thousands
            if "," in cleaned:
                return float(cleaned.replace(",", ""))

            # Case 2: has dot but likely thousands separator
            if "." in cleaned:
                parts = cleaned.split(".")
                if len(parts[-1]) == 3:  # e.g., 1.250 → 1250
                    return float(cleaned.replace(".", ""))

            value = float(cleaned)

            # OCR decimal shift fix
            digits = len(re.sub(r"[^\d]", "", original))

            if value < 10 and digits >= 4:
                return value * 1000
            elif value < 100 and digits >= 4:
                return value * 10

            return value

        return float(amount)

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
        content = content.strip()
        content = re.sub(r"```json", "", content)
        content = re.sub(r"```", "", content)
        content = content.strip()

        data = json.loads(content)

        # NORMALIZE DATA
        data["amount"] = normalize_amount(data.get("amount"))
        data["date"] = normalize_date(data.get("date"))
        data["vendor"] = (data.get("vendor") or "").lower().strip()

        # ADD CONFIDENCE SCORE
        confidence = calculate_confidence(data)
        data["ai_confidence"] = confidence

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