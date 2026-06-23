import json, httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from .config import DEEPSEEK_API_KEY, DEEPSEEK_CHAT_URL, EXPOSE_REASONING_CONTENT
from .database import log_usage, deduct_upstream_cost, calculate_upstream_cost

def _strip_reasoning(data):
    if EXPOSE_REASONING_CONTENT: return data
    for c in data.get("choices",[]):
        m = c.get("message")
        if isinstance(m, dict): m.pop("reasoning_content", None)
    return data

def _filter_sse(line):
    if not line.startswith("data: "): return line + "\n"
    payload = line[6:]
    if payload.strip() == "[DONE]": return line + "\n"
    if EXPOSE_REASONING_CONTENT: return line + "\n"
    try: obj = json.loads(payload)
    except: return line + "\n"
    modified = False
    for c in obj.get("choices",[]):
        d = c.get("delta",{})
        if "reasoning_content" in d: del d["reasoning_content"]; modified = True
    for c in obj.get("choices",[]):
        d = c.get("delta",{})
        if not d and c.get("finish_reason") is None: return None
    return ("data: " + json.dumps(obj, ensure_ascii=False) + "\n") if modified else line + "\n"

async def proxy_chat_completions(body, stream=False, key_info=None):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    fb = {}
    for f in ["messages","model","temperature","max_tokens","top_p","frequency_penalty","presence_penalty","stop","stream","stream_options","user"]:
        if f in body: fb[f] = body[f]
    fb["stream"] = stream
    model = body.get("model","unknown")
    timeout = httpx.Timeout(120.0, connect=10.0)
    if stream: return await _ps(headers, fb, timeout, key_info, model)
    else: return await _psync(headers, fb, timeout, key_info, model)

async def _psync(headers, body, timeout, key_info, model):
    ki = key_info or {}
    async with httpx.AsyncClient(timeout=timeout) as c:
        try:
            r = await c.post(DEEPSEEK_CHAT_URL, headers=headers, json=body)
            data = r.json()
        except Exception as e:
            log_usage(ki.get("id",0), ki.get("key_prefix","?"), model, None, 500, str(e)[:500])
            raise HTTPException(502, detail=f"Upstream failed: {str(e)[:200]}")
        if r.status_code == 200:
            usage = data.get("usage",{})
            cost = calculate_upstream_cost(model, usage)
            log_usage(ki.get("id",0), ki.get("key_prefix","?"), model, usage, 200, upstream_cost=cost)
            if cost > 0 and ki.get("id"):
                deduct_upstream_cost(ki["id"], cost)
            return JSONResponse(content=_strip_reasoning(data))
        else:
            em = data.get("error",{}).get("message", r.text[:500])
            log_usage(ki.get("id",0), ki.get("key_prefix","?"), model, None, r.status_code, str(em)[:500])
            raise HTTPException(r.status_code, detail=f"Upstream error: {em}")

async def _ps(headers, body, timeout, key_info, model):
    ki = key_info or {}
    ud = {"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}
    fs = 200; em = None

    async def gen():
        nonlocal ud, fs, em
        buf = b""
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                async with c.stream("POST", DEEPSEEK_CHAT_URL, headers=headers, json=body) as r:
                    if r.status_code != 200:
                        fs = r.status_code; eb = await r.aread()
                        em = eb.decode(errors="replace")[:500]
                        yield f"data: {json.dumps({'error':f'Upstream error: {em}'})}\n\n".encode()
                        yield b"data: [DONE]\n\n"; return
                    async for ch in r.aiter_bytes():
                        buf += ch
                        while b"\n\n" in buf:
                            ev, buf = buf.split(b"\n\n", 1)
                            es = ev.decode(errors="replace")
                            for line in es.split("\n"):
                                if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                                    try:
                                        obj = json.loads(line[6:])
                                        u = obj.get("usage")
                                        if u:
                                            for k in ("prompt_tokens","completion_tokens","total_tokens"):
                                                ud[k] += u.get(k,0)
                                    except: pass
                            ol = []
                            for line in es.split("\n"):
                                if not line: continue
                                f = _filter_sse(line)
                                if f is not None: ol.append(f.rstrip("\n"))
                            if ol: yield ("\n".join(ol) + "\n\n").encode()
                    if buf:
                        f = _filter_sse(buf.decode(errors="replace").rstrip("\n"))
                        if f is not None: yield f.encode()
        except Exception as e:
            fs = 500; em = str(e)[:500]
            yield f"data: {json.dumps({'error':str(e)[:200]})}\n\n".encode()
            yield b"data: [DONE]\n\n"

    resp = StreamingResponse(gen(), media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","Connection":"keep-alive"})
    import asyncio
    async def after():
        await asyncio.sleep(0)
        cost = calculate_upstream_cost(model, ud) if fs == 200 else 0.0
        log_usage(ki.get("id",0), ki.get("key_prefix","?"), model, ud, fs, em, upstream_cost=cost)
        if fs == 200 and ki.get("id"):
            if cost > 0: deduct_upstream_cost(ki["id"], cost)
    resp.background = after
    return resp