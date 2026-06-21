from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from .auth import verify_api_key
from .proxy import proxy_chat_completions
from .config import EXPOSED_MODELS
from .database import init_db

# Initialize database on startup
init_db()

app = FastAPI(title="DeepSeek API Gateway", version="0.2.0")


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
            detail=f"Model '{model}' not supported. Available: {', '.join(EXPOSED_MODELS)}",
        )

    stream = body.get("stream", False)
    return await proxy_chat_completions(body, stream=stream, key_info=key_info)


@app.get("/health")
async def health():
    return {"status": "ok"}