from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .auth import verify_api_key
from .proxy import proxy_chat_completions
from .config import EXPOSED_MODELS
from .database import init_db, get_db, get_key_usage, create_order, get_order_status

# Initialize database on startup
init_db()

app = FastAPI(title="DeepSeek API Gateway", version="0.4.0")


@app.get("/v1/models")
async def list_models(key_info: dict = Depends(verify_api_key)):
    """Return list of supported models (OpenAI-compatible format)."""
    return JSONResponse(content={
        "object": "list",
        "data": [
            {"id": m, "object": "model", "owned_by": "deepseek-gateway"}
            for m in EXPOSED_MODELS
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
    if model not in EXPOSED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model!r} not supported. Available: {chr(44).join(EXPOSED_MODELS)}",
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
    """Return available packages (public endpoint)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, token_quota, rate_limit, description FROM packages WHERE is_active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return JSONResponse(content={"packages": [dict(r) for r in rows]})


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
    telegram_or_discord = (body.get("telegram_or_discord") or "").strip()
    use_case = (body.get("use_case") or "").strip()
    try:
        expected_daily_tokens = int(body.get("expected_daily_tokens", 0))
    except (ValueError, TypeError):
        expected_daily_tokens = 0
    selected_plan = body.get("selected_plan", "")
    package_id = None
    if selected_plan:
        conn = get_db()
        pkg = conn.execute("SELECT id FROM packages WHERE name=? AND is_active=1", (selected_plan,)).fetchone()
        conn.close()
        if pkg:
            package_id = pkg["id"]
    if not package_id:
        package_id = 1  # default to Trial

    order = create_order(email, telegram_or_discord, use_case, expected_daily_tokens, package_id)
    return JSONResponse(content={
        "order_id": order["order_id"],
        "status": order["status"],
        "package": order["package_name"],
        "token_quota": order["token_quota"],
        "payment_status": "unpaid",
        "order_url": f"/order.html?order_id={order['order_id']}",
        "message": "Your application has been received. Save your Order ID to check status.",
    })


@app.get("/api/order/status")
async def order_status(order_id: int = Query(...), email: str = Query(...)):
    """Public order status lookup. Requires matching email."""
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    result, err = get_order_status(order_id, email)
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


# Static files must be mounted last (after all API routes)
import os as _os
_static_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "static")
if _os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")