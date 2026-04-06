from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from dotenv import load_dotenv

# Load environment FIRST
load_dotenv()

print("OPENAI KEY LOADED:", os.getenv("OPENAI_API_KEY"))

# Routers
from routes.mileage_routes import router as mileage_router
from routes.auth_routes import router as auth_router
from routes.gmail_routes import router as gmail_router
from routes.xero_routes import router as xero_router
from routes.stripe_routes import router as stripe_router
from routes.chatbot_routes import router as chatbot_router
from routes.receipt_routes import router as receipt_router
from routes.report_routes import router as report_router
from routes.transaction_routes import router as transaction_router
app = FastAPI(title="TaxMind AI Backend")

# Serve uploaded receipt images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mileage_router)
app.include_router(auth_router)
app.include_router(gmail_router)
app.include_router(xero_router)
app.include_router(stripe_router)
app.include_router(chatbot_router)
app.include_router(receipt_router)
app.include_router(report_router)
app.include_router(transaction_router)

@app.get("/")
def home():
    return {"message": "TaxMind AI Backend Running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)