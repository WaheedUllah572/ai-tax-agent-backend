from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import stripe
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

router = APIRouter(tags=["Stripe"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY is missing")

stripe.api_key = STRIPE_SECRET_KEY


class CheckoutRequest(BaseModel):
    additional_accounts: int = 0
    quickbooks: bool = False


@router.post("/create-checkout-session")
def create_checkout_session(data: CheckoutRequest):
    try:
        base_price = 10
        account_price = data.additional_accounts * 5
        quickbooks_price = 2 if data.quickbooks else 0

        total_price = base_price + account_price + quickbooks_price

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "TaxMate Subscription",
                            "description": "AI Tax Agent (Max)",
                        },
                        "unit_amount": total_price * 100,
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{FRONTEND_URL}/subscription-success",
            cancel_url=f"{FRONTEND_URL}/subscription-cancel",
        )

        return {"url": session.url}

    except Exception as e:
        print("STRIPE ERROR:", str(e))  # 👈 critical for debugging
        raise HTTPException(status_code=500, detail=str(e))
