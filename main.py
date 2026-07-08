from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.settings_routes import router as settings_router
from routes.onboarding_routes import router as onboarding_router
from routes.accountant_routes import router as accountant_router
import uvicorn
import os

from dotenv import load_dotenv

# =====================================
# LOAD ENV VARIABLES
# =====================================
load_dotenv()

print(
    "OPENAI KEY LOADED:",
    os.getenv("OPENAI_API_KEY")
)

# =====================================
# IMPORT ROUTERS
# =====================================
from routes.mileage_routes import router as mileage_router
from routes.auth_routes import router as auth_router
from routes.accountant_routes import router as accountant_router
from routes.gmail_routes import router as gmail_router
from routes.xero_routes import router as xero_router
from routes.stripe_routes import router as stripe_router
from routes.chatbot_routes import router as chatbot_router
from routes.receipt_routes import router as receipt_router
from routes.report_routes import router as report_router
from routes.transaction_routes import router as transaction_router
from routes.calendar_routes import router as calendar_router
# =====================================
# FASTAPI APP
# =====================================
app = FastAPI(
    title="TaxMind AI Backend"
)

# =====================================
# CREATE UPLOADS FOLDER
# =====================================
if not os.path.exists("uploads"):

    os.makedirs("uploads")

# =====================================
# SERVE UPLOADED FILES
# =====================================
app.mount(

    "/uploads",

    StaticFiles(directory="uploads"),

    name="uploads"
)

# =====================================
# PERMANENT PRODUCTION CORS FIX
# =====================================
app.add_middleware(

    CORSMiddleware,

    # LOCALHOST FOR DEVELOPMENT
    allow_origins=[
        "http://localhost:3000"
    ],

    # ALLOW ALL VERCEL DEPLOYMENTS
    allow_origin_regex=r"https://.*\.vercel\.app",

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# =====================================
# ROUTES
# =====================================
app.include_router(mileage_router)

app.include_router(auth_router)

app.include_router(gmail_router)

app.include_router(accountant_router)

app.include_router(accountant_router)

app.include_router(xero_router)

app.include_router(stripe_router)

app.include_router(chatbot_router)

app.include_router(receipt_router)

app.include_router(report_router)
app.include_router(onboarding_router)
app.include_router(transaction_router)
app.include_router(settings_router)
app.include_router(calendar_router)
# =====================================
# ROOT
# =====================================
@app.get("/")
def home():

    return {

        "message":
            "TaxMind AI Backend Running"
    }

# =====================================
# RUN SERVER
# =====================================
if __name__ == "__main__":

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                8000
            )
        )
    )