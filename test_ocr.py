import asyncio

from receipt_ai import analyze_receipt_image

file_path = "uploads/demo-uber-receipt.PNG"

with open(file_path, "rb") as f:
    file_bytes = f.read()

result = asyncio.run(analyze_receipt_image(file_bytes))

print(result)