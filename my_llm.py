from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, ZHIPU_API_KEY, \
    ZHIPU_BASE_URL, HUNYUAN_API_KEY, HUNYUAN_BASE_URL, DOUBAO_API_KEY, DOUBAO_BASE_URL

# 初始化模型函数
def init_models():
    global deepseek_llm, dashscope_llm, zhipu_llm, hunyuan_llm, dashscope_vision_llm, doubao_llm
    
    # 初始化Deepseek模型
    try:
        deepseek_llm = init_chat_model(
            model="deepseek-chat",
            model_provider="deepseek",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    except Exception as e:
        print(f"初始化Deepseek模型失败: {e}")
        deepseek_llm = None
    
    # 初始化千问模型
    try:
        dashscope_llm = init_chat_model(
            model="qwen-plus",
            model_provider="openai",
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
    except Exception as e:
        print(f"初始化千问模型失败: {e}")
        dashscope_llm = None
    
    # 初始化支持图片理解的千问模型
    try:
        dashscope_vision_llm = ChatOpenAI(
            model="qwen-vl-max",
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            max_retries=3,
        )
    except Exception as e:
        print(f"初始化支持图片理解的千问模型失败: {e}")
        dashscope_vision_llm = None
    
    # 初始化智谱模型
    try:
        zhipu_llm = init_chat_model(
            model="glm-5",
            model_provider="openai",
            api_key=ZHIPU_API_KEY,
            base_url=ZHIPU_BASE_URL,
        )
    except Exception as e:
        print(f"初始化智谱模型失败: {e}")
        zhipu_llm = None
    
    # 初始化混元模型
    try:
        hunyuan_llm = init_chat_model(
            model="hunyuan-turbos-latest",
            model_provider="openai",
            api_key=HUNYUAN_API_KEY,
            base_url=HUNYUAN_BASE_URL,
        )
    except Exception as e:
        print(f"初始化混元模型失败: {e}")
        hunyuan_llm = None
    
    # 初始化豆包模型
    try:
        doubao_llm = init_chat_model(
            model="Doubao-Seed-1.8",
            model_provider="openai",
            api_key=DOUBAO_API_KEY,
            base_url=DOUBAO_BASE_URL,
        )
    except Exception as e:
        print(f"初始化豆包模型失败: {e}")
        doubao_llm = None

# 初始化模型
try:
    init_models()
except Exception as e:
    print(f"初始化模型失败: {e}")
    # 确保所有模型变量都有默认值
    deepseek_llm = None
    dashscope_llm = None
    zhipu_llm = None
    hunyuan_llm = None
    dashscope_vision_llm = None
    doubao_llm = None