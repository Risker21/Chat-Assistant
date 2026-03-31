import os
from dotenv import load_dotenv

load_dotenv(override=True)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL")

HUNYUAN_API_KEY = os.getenv("HUNYUAN_API_KEY")
HUNYUAN_BASE_URL = os.getenv("HUNYUAN_BASE_URL")

DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")
ARK_API_KEY = os.getenv("ARK_API_KEY")
DOUBAO_BASE_URL = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL", "https://api.tavily.com")
