import os
import json
import base64
import re
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
import io

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def convert_to_jpeg(file_bytes: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()
    except Exception as e:
        print("IMAGE CONVERT ERROR:", e)
        return None


def analyze_receipt_image(file_bytes: bytes) -> dict:
    try:
        # Convert to JPEG
        file_bytes = convert_to_jpeg(file_bytes)
        if not file_bytes:
            return {
                "vendor": "Invalid Image",
                "date": "",
                "amount": "0.00",
                "category": "Uncategorized",
                "document_type": "Unknown",
                "deduction_type": "Uncategorized"
            }

        base64_image = base64.b64encode(file_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},  # FORCE JSON
            messages=[
                {
                    "role": "system",
                    "content": "Extract receipt data and return JSON with vendor, date, amount, category, document_type, deduction_type."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this receipt."},
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
        return json.loads(content)

    except Exception as e:
        print("OPENAI ERROR:", e)
        return {
            "vendor": "Processing Error",
            "date": "",
            "amount": "0.00",
            "category": "Uncategorized",
            "document_type": "Unknown",
            "deduction_type": "Uncategorized"
        }