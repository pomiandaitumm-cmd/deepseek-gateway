from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .auth import verify_api_key
from .proxy import proxy_chat_completions
from .config import EXPOSED_MODELS
from .database import (init_db, get_db, get_key_usage, create_order, get_order_status, get_lead_stats, checkout_order, get_order_status_v07)

# Initialize database on startup
init_db()

app = FastAPI(title="DeepSeek API Gateway", version="0.7.0")


@app.get("/v1/models")
async def list_models(key_info: dict = Depends(verify_api_key)):
    """Return list of models available for this key (based on plan)."""
    # Use key's allowed_models from DB (set during approve_order)
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
    # Check if key's plan allows this model
    allowed = key_info.get("allowed_models", "")
    if allowed:
        allowed_list = [m.strip() for m in allowed.split(",") if m.strip()]
        if model not in allowed_list:
            raise HTTPException(
                status_code=403,
                detail="Your plan does not include this model",
            )
    # Fallback: check against global exposed models
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
        package_id = 1  # default to Trial

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
    result, err = get_order_status_v07(order_id, email)
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



# v0.7 Payment endpoints

@app.post("/api/checkout")
async def api_checkout(request: Request):
    """Create a checkout order with unique payment amount."""
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

    order, err = checkout_order(email, plan, source=source, ref=ref)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return JSONResponse(content=order)


@app.get("/api/payment/config")
async def payment_config():
    """Return payment configuration for frontend display."""
    import os
    return JSONResponse(content={
        "network": os.getenv("PAYMENT_NETWORK", "TRC20"),
        "token": os.getenv("PAYMENT_TOKEN", "USDT"),
        "enabled": bool(os.getenv("PAYMENT_ADDRESS", "")),
        "expiry_minutes": int(os.getenv("ORDER_EXPIRY_MINUTES", "30")),
    })

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
