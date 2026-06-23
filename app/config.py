import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Upstream DeepSeek URL
DEEPSEEK_CHAT_URL = f"{DEEPSEEK_BASE_URL}/chat/completions"
DEEPSEEK_MODELS_URL = f"{DEEPSEEK_BASE_URL}/models"

# Models exposed by this gateway
EXPOSED_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]

# Whether to expose reasoning content (default false = filter it out)
EXPOSE_REASONING_CONTENT = os.getenv("EXPOSE_REASONING_CONTENT", "false").lower() == "true"
# v0.7 Payment System
PAYMENT_ADDRESS = os.getenv("PAYMENT_ADDRESS", "")
PAYMENT_NETWORK = os.getenv("PAYMENT_NETWORK", "TRC20")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "USDT")
TRONGRID_API_BASE = os.getenv("TRONGRID_API_BASE", "https://api.trongrid.io")
PAYMENT_POLL_INTERVAL = int(os.getenv("PAYMENT_POLL_INTERVAL", "30"))
ORDER_EXPIRY_MINUTES = int(os.getenv("ORDER_EXPIRY_MINUTES", "30"))