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