# DeepSeek API Gateway

OpenAI-compatible API proxy that forwards client requests to DeepSeek official API.

## Project Structure

`
deepseek-gateway/
+-- app/
|   +-- __init__.py
|   +-- main.py          # FastAPI app, routes
|   +-- config.py        # Env vars
|   +-- auth.py          # API key verification (SQLite)
|   +-- database.py      # SQLite db layer
|   +-- proxy.py         # Forward to DeepSeek + log usage
+-- create_key.py        # Create API keys
+-- disable_key.py       # Disable API keys
+-- usage_report.py      # Usage statistics
+-- Dockerfile
+-- docker-compose.yml
+-- deploy.sh            # VPS deployment script
+-- upload.ps1           # Upload to VPS (PowerShell)
+-- .env.example
+-- .env                 # Real keys (never commit!)
+-- requirements.txt
+-- test_client.py
+-- README.md
`

## Local Development

### 1. Setup

`powershell
cd deepseek-gateway
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
`

### 2. Configure

Copy .env.example to .env and fill in your key:

`
DEEPSEEK_API_KEY=sk-xxxxxxxx
`

### 3. Create API Keys

`powershell
python create_key.py --name "user-a" --rate-limit 30
`

Save the full key shown on screen -- it will NOT be shown again.

### 4. Run

`powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
`

### 5. Test

`powershell
python test_client.py <your-api-key>
`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /v1/models | List available models |
| POST | /v1/chat/completions | Chat completions (supports stream) |
| GET | /health | Health check |

Auth: Authorization: Bearer <your-gateway-key>

## Client Usage

`python
from openai import OpenAI

client = OpenAI(
    api_key="sk-gateway-xxxx",
    base_url="http://your-server:8000/v1",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
`

## VPS Deployment (Docker)

### 1. Edit upload.ps1

Set your VPS IP, username, port.

### 2. Upload and deploy

`powershell
.\upload.ps1
`

This will scp the project, run deploy.sh which:
- Installs docker + nginx
- Creates data/ directory for persistent SQLite
- Starts container with docker compose up -d --build
- Configures nginx reverse proxy (port 80 -> container 8000)

### 3. Subsequent uploads

upload.ps1 excludes data/ and db.sqlite3 -- your user keys and usage logs will NOT be overwritten.

## Managing API Keys

`ash
# Create a key
python create_key.py --name "alice" --rate-limit 30

# List usage
python usage_report.py

# Disable a key
python disable_key.py --prefix sk-gateway-xxxx
`

In Docker:
`ash
docker exec deepseek-gateway python create_key.py --name "alice" --rate-limit 30
docker exec deepseek-gateway python usage_report.py
`

## Architecture

`
User (sk-gateway-xxxx)
    |
    v
Nginx :80 -> 127.0.0.1:8000
    |
    v
Your Gateway (FastAPI + SQLite)
    |  Bearer DEEPSEEK_API_KEY
    v
DeepSeek Official API (api.deepseek.com)
`

Your DeepSeek API key stays on the server. Users only know their sk-gateway-* keys.
Key hashes stored in SQLite. Database persisted at ./data/db.sqlite3.