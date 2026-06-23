"""
PayPal integration module.
Supports Sandbox and Live via PAYPAL_MODE env var.
Uses PayPal REST API directly (no SDK dependency needed).
"""
import os
import httpx
import json

PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox").lower()
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_CURRENCY = os.getenv("PAYPAL_CURRENCY", "USD")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://modelrelayapis.cc")

SANDBOX_API = "https://api-m.sandbox.paypal.com"
LIVE_API = "https://api-m.paypal.com"

def get_api_base():
    return LIVE_API if PAYPAL_MODE == "live" else SANDBOX_API

def is_configured():
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)

async def get_access_token():
    """Get PayPal OAuth2 access token."""
    if not is_configured():
        return None, "PayPal is not configured (missing CLIENT_ID or CLIENT_SECRET)"
    base = get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        if resp.status_code != 200:
            return None, f"PayPal auth failed: {resp.status_code} {resp.text[:200]}"
        data = resp.json()
        return data.get("access_token"), None

async def create_paypal_order(paypal_order_id: str, amount_usd: float, currency: str = None):
    """Create a PayPal order. paypal_order_id is our local identifier for idempotency."""
    if not is_configured():
        return None, "PayPal is not configured"
    token, err = await get_access_token()
    if err:
        return None, err

    currency = currency or PAYPAL_CURRENCY
    amount_str = f"{amount_usd:.2f}"
    base = get_api_base()

    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": str(paypal_order_id),
            "amount": {
                "currency_code": currency,
                "value": amount_str,
            },
        }],
        "payment_source": {
            "paypal": {
                "experience_context": {
                    "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                    "brand_name": "DeepSeek Gateway",
                    "locale": "en-US",
                    "landing_page": "LOGIN",
                    "user_action": "PAY_NOW",
                    "return_url": f"{SITE_BASE_URL}/order.html",
                    "cancel_url": f"{SITE_BASE_URL}/pricing.html",
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": f"local-{paypal_order_id}",
            },
            json=body,
            timeout=15.0,
        )
        if resp.status_code not in (200, 201):
            return None, f"PayPal create order failed: {resp.status_code} {resp.text[:300]}"
        return resp.json(), None

async def capture_paypal_order(paypal_order_id: str):
    """Capture a PayPal order after user approval."""
    if not is_configured():
        return None, "PayPal is not configured"
    token, err = await get_access_token()
    if err:
        return None, err

    base = get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        if resp.status_code not in (200, 201):
            return None, f"PayPal capture failed: {resp.status_code} {resp.text[:300]}"
        data = resp.json()
        if data.get("status") != "COMPLETED":
            return None, f"PayPal capture not completed: status={data.get('status')}"
        return data, None
