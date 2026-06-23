from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .auth import verify_api_key
from .proxy import proxy_chat_completions
from .config import EXPOSED_MODELS
from .paypal import (
    is_configured as paypal_configured,
    PAYPAL_CLIENT_ID,
    PAYPAL_CURRENCY,
    PAYPAL_MODE,
    create_paypal_order as paypal_create,
    capture_paypal_order as paypal_capture,
)
from .database import (
    init_db, get_db, get_key_usage, create_order, get_order_status,
    get_lead_stats, checkout_order, get_order_status_v07,
    checkout_order_paypal, capture_paypal_and_approve, get_order_status_v08,
)

# Initialize database on startup
init_db()

app = FastAPI(title="DeepSeek API Gateway", version="0.8.0")


@app.get("/v1/models")
async def list_models(key_info: dict = Depends(verify_api_key)):
    """Return list of models available for this key (based on plan)."""
    conn = get_db()
    row = conn.execute("SELECT allowed_models FROM api_keys WHERE id=?", (key_info["id"],)).fetchone()
    conn.close()
    if row and row["allowed_models"]:
        models = [m.strip() for m in row["allowed_models"].split(",") if m.strip()]
    else:
        models = list(EXPOSED_MODELS)
    return JSONResponse(content={
        "object": "list",
        "data": [
            {"id": m, "object": "model", "owned_by": "deepseek-gateway"}
            for m in models
        ],
    })


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, key_info: dict = Depends(verify_api_key)):
    """OpenAI-compatible chat completions endpoint with usage tracking."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "")
    allowed = key_info.get("allowed_models", "")
    if allowed:
        allowed_list = [m.strip() for m in allowed.split(",") if m.strip()]
        if model not in allowed_list:
            raise HTTPException(
                status_code=403,
                detail="Your plan does not include this model",
            )
    if model not in EXPOSED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model!r} not supported. Available: {', '.join(EXPOSED_MODELS)}",
        )

    stream = body.get("stream", False)
    return await proxy_chat_completions(body, stream=stream, key_info=key_info)


@app.get("/v1/key/usage")
async def key_usage(key_info: dict = Depends(verify_api_key)):
    """Return usage stats for the authenticated API key."""
    usage = get_key_usage(key_info["id"])
    if usage is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve usage data")
    return JSONResponse(content=usage)


@app.get("/api/packages")
async def list_all_packages():
    """Return available packages with pricing (public endpoint)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, token_quota, rate_limit, price_usd, allowed_models, description FROM packages WHERE is_active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    pkgs = []
    for r in rows:
        d = dict(r)
        d["allowed_models"] = [m.strip() for m in (d.get("allowed_models") or "").split(",") if m.strip()]
        pkgs.append(d)
    return JSONResponse(content={"packages": pkgs})


@app.post("/api/apply")
async def apply_for_access(request: Request):
    """Submit an application for API access."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    telegram_or_discord = (body.get("telegram_or_discord") or body.get("contact") or "").strip()
    use_case = (body.get("use_case") or body.get("intended_use") or "").strip()
    try:
        expected_daily_tokens = int(body.get("expected_daily_tokens", 0))
    except (ValueError, TypeError):
        expected_daily_tokens = 0
    source = (body.get("source") or "").strip()
    ref = (body.get("ref") or "").strip()
    if not source and ref:
        source = ref
    selected_plan = body.get("selected_plan", body.get("plan", ""))
    package_id = None
    if selected_plan:
        conn = get_db()
        pkg = conn.execute("SELECT id FROM packages WHERE name=? AND is_active=1", (selected_plan,)).fetchone()
        conn.close()
        if pkg:
            package_id = pkg["id"]
    if not package_id:
        package_id = 1

    order = create_order(email, telegram_or_discord, use_case, expected_daily_tokens, package_id, source=source, ref=ref)
    return JSONResponse(content={
        "order_id": order["order_id"],
        "status": order["status"],
        "package": order["package_name"],
        "token_quota": order["token_quota"],
        "payment_status": "unpaid",
        "price_usd": order.get("price_usd", 0),
        "order_url": f"/order.html?order_id={order['order_id']}",
        "message": "Your application has been received. Save your Order ID to check status.",
    })


@app.get("/api/order/status")
async def order_status(order_id: int = Query(...), email: str = Query(...)):
    """Public order status lookup. Requires matching email."""
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    result, err = get_order_status_v08(order_id, email)
    if err:
        if "not found" in err.lower():
            raise HTTPException(status_code=404, detail=err)
        if "email" in err.lower():
            raise HTTPException(status_code=403, detail=err)
        raise HTTPException(status_code=400, detail=err)
    return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ===== v0.8 PayPal Endpoints =====

@app.get("/api/paypal/config")
async def paypal_config():
    """Return PayPal configuration for frontend. Does NOT expose client_secret."""
    return JSONResponse(content={
        "client_id": PAYPAL_CLIENT_ID,
        "currency": PAYPAL_CURRENCY,
        "mode": PAYPAL_MODE,
        "enabled": paypal_configured(),
    })


@app.post("/api/paypal/create-order")
async def paypal_create_order(request: Request):
    """Create a PayPal order and a local pending order.
    Frontend calls PayPal SDK with the returned paypal_order_id."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    plan = (body.get("plan") or "Trial").strip()
    source = (body.get("source") or "").strip()
    ref = (body.get("ref") or "").strip()

    # First create local order to get an order_id for PayPal reference
    local_order, err = checkout_order_paypal(email, plan, "__pending__", source=source, ref=ref)
    if err:
        raise HTTPException(status_code=400, detail=err)

    local_order_id = local_order["order_id"]
    price_usd = local_order["price_usd"]

    # Now create PayPal order using our local_order_id as reference
    pp_result, pp_err = await paypal_create(str(local_order_id), price_usd)
    if pp_err:
        raise HTTPException(status_code=502, detail=f"PayPal error: {pp_err}")

    paypal_order_id = pp_result.get("id")
    if not paypal_order_id:
        raise HTTPException(status_code=502, detail="PayPal did not return an order ID")

    # Update local order with real PayPal order ID
    conn = get_db()
    conn.execute(
        "UPDATE orders SET paypal_order_id=? WHERE id=?",
        (paypal_order_id, local_order_id))
    conn.commit()
    conn.close()

    return JSONResponse(content={
        "order_id": local_order_id,
        "paypal_order_id": paypal_order_id,
        "status": "pending",
        "plan": plan,
        "price_usd": price_usd,
        "token_quota": local_order["token_quota"],
        "email": email,
        "status_url": f"/order.html?order_id={local_order_id}&email={email}",
        "message": "Complete your PayPal payment to receive your API key.",
    })


@app.post("/api/paypal/capture-order")
async def paypal_capture_order(request: Request):
    """Capture a PayPal order after user approval in PayPal UI.
    Auto-approves the local order and generates API key."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    paypal_order_id = (body.get("paypal_order_id") or "").strip()
    if not paypal_order_id:
        raise HTTPException(status_code=400, detail="paypal_order_id is required")
    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")

    # Find local order by paypal_order_id
    conn = get_db()
    order_row = conn.execute(
        "SELECT o.*, c.email FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.paypal_order_id=?",
        (paypal_order_id,)).fetchone()
    conn.close()

    if not order_row:
        raise HTTPException(status_code=404, detail="Order not found for this PayPal order ID")

    # Verify email matches
    if order_row["email"].lower() != email.lower():
        raise HTTPException(status_code=403, detail="Email does not match this order")

    local_order_id = order_row["id"]

    # If already approved, return existing key
    if order_row["status"] == "approved" and order_row["issued_key"]:
        pkg = get_db().execute("SELECT token_quota FROM packages WHERE id=?", (order_row["package_id"],)).fetchone()
        return JSONResponse(content={
            "order_id": local_order_id,
            "status": "approved",
            "full_key": order_row["issued_key"],
            "key_prefix": order_row["key_prefix"],
            "token_quota": pkg["token_quota"] if pkg else 0,
            "status_url": f"/order.html?order_id={local_order_id}&email={email}",
            "message": "Your API key is ready. Save it now.",
        })

    # Capture the PayPal order
    capture_result, capture_err = await paypal_capture(paypal_order_id)
    if capture_err:
        raise HTTPException(status_code=502, detail=f"PayPal capture failed: {capture_err}")

    # Mark paid and auto-approve
    result, err = capture_paypal_and_approve(local_order_id, paypal_order_id)
    if err:
        raise HTTPException(status_code=500, detail=f"Approval failed: {err}")

    return JSONResponse(content={
        "order_id": local_order_id,
        "status": "approved",
        "full_key": result.get("full_key", ""),
        "key_prefix": result.get("key_prefix", ""),
        "token_quota": result.get("token_quota", 0),
        "status_url": f"/order.html?order_id={local_order_id}&email={email}",
        "message": "Payment confirmed! Your API key is ready.",
    })


# ===== Legacy checkout (kept for backward compat) =====

@app.post("/api/checkout")
async def api_checkout(request: Request):
    """Create a checkout order. Uses PayPal flow if configured, else falls back to manual."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    plan = (body.get("plan") or "Trial").strip()
    source = (body.get("source") or "").strip()
    ref = (body.get("ref") or "").strip()

    # Legacy fallback – creates order without payment linkage
    order, err = checkout_order_paypal(email, plan, "", source=source, ref=ref)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return JSONResponse(content=order)


# Static file mount (after all API routes)
import os as _os
_static_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "static")
if _os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


@app.get("/api/admin/lead-stats")
async def lead_stats(key_info: dict = Depends(verify_api_key)):
    """Admin: return lead source statistics. Requires valid API key."""
    stats = get_lead_stats()
    return JSONResponse(content=stats)
