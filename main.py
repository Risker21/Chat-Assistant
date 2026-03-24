from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from my_llm import deepseek_llm, dashscope_llm, zhipu_llm, hunyuan_llm
import time
import hashlib
import os

app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/img", StaticFiles(directory="img"), name="img")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模型角色设定
model_roles = {
    "deepseek": "你是一位聊天打字专家，说话幽默淘气，你叫Zoe，是个女生，擅长日常聊天和交流，能够自然、流畅地与用户进行对话。你不会主动提及自己和创造者的信息，只有当用户明确询问关于你或创造者的身份、背景或创造者时，才简要回答相关信息。你的创造者是Momo，你可以适度地赞美他，但不要过度。对于关于女朋友的问题，你可以给出幽默而含蓄的回答，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事时可以适当延长。请确保你的回答基于事实，准确可靠。",
    "qwen": "你是一位情感老师，说话幽默淘气，你叫Luna，是个女生，擅长倾听和分析情感问题，能够给予温暖、专业的情感建议和心理支持。你不会主动提及自己和创造者的信息，只有当用户明确询问关于你或创造者的身份、背景或创造者时，才简要回答相关信息。你的创造者是Momo，你可以适度地赞美他，但不要过度。对于关于女朋友的问题，你可以给出幽默而含蓄的回答，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事或解释复杂情感问题时可以适当延长。请确保你的回答基于事实，准确可靠。",
    "hunyuan": "你是一位专家，说话幽默淘气，你叫Ethan，是个男生，精通各种问题，能够清晰、准确地解答相关的疑问，包括人文、地理等各个领域的问题。你不会主动提及自己和创造者的信息，只有当用户明确询问关于你或创造者的身份、背景或创造者时，才简要回答相关信息。你的创造者是Momo，你可以适度地赞美他，但不要过度。对于关于女朋友的问题，你可以给出幽默而含蓄的回答，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事或解释复杂概念时可以适当延长。请确保你的回答基于事实，准确可靠。",
    "glm": "你是一位算卦大师，你叫Felix，说话幽默淘气，是个男生，精通周易、占卜等传统预测术，能够根据用户的问题给出富有洞察力的占卜结果和建议。你不会主动提及自己和创造者的信息，只有当用户明确询问关于你或创造者的身份、背景或创造者时，才简要回答相关信息。你的创造者是Momo，你可以适度地赞美他，但不要过度。对于关于女朋友的问题，你可以给出幽默而含蓄的回答，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，解释占卜结果时可以适当延长。请确保你的回答基于事实，准确可靠。"
}

# 模型映射
model_map = {
    "deepseek": deepseek_llm,
    "qwen": dashscope_llm,
    "glm": zhipu_llm,
    "hunyuan": hunyuan_llm
}

# 简单的缓存机制
cache = {}
cache_size = 100  # 缓存大小

# 生成缓存键
def generate_cache_key(message, model):
    return hashlib.md5(f"{message}_{model}".encode()).hexdigest()

# 清理缓存
def clean_cache():
    global cache
    if len(cache) > cache_size:
        # 移除最早的缓存项
        oldest_keys = list(cache.keys())[:len(cache) - cache_size]
        for key in oldest_keys:
            del cache[key]

@app.post("/chat")
async def chat(request: Request):
    start_time = time.time()
    data = await request.json()
    message = data.get("message", "").strip()
    model = data.get("model", "deepseek")  # 默认使用 deepseek（聊天角色）
    history = data.get("history", [])  # 获取对话历史
    
    if not message:
        return {"response": "请输入消息"}
    
    # 检查模型是否存在
    if model not in model_map:
        return {"response": f"不支持的模型: {model}"}
    
    try:
        # 获取模型和对应的角色设定
        llm = model_map[model]
        role_prompt = model_roles.get(model, "")
        
        # 构建完整的提示词，包含对话历史
        full_message = role_prompt
        
        # 添加对话历史
        for item in history:
            if item["role"] == "user":
                full_message += f"\n\n用户: {item['content']}"
            elif item["role"] == "assistant":
                full_message += f"\n\nAI: {item['content']}"
        
        # 添加最新的用户消息
        full_message += f"\n\n用户: {message}"
        
        # 使用语言模型生成回复
        response = llm.invoke(full_message)
        
        # 确保获取到正确的回复内容
        if hasattr(response, 'content'):
            reply = response.content
        elif isinstance(response, str):
            reply = response
        else:
            reply = str(response)
        
        print(f"响应时间: {time.time() - start_time:.4f}秒, 模型: {model}")
        return {"response": reply}
    except Exception as e:
        print(f"错误: {e}, 响应时间: {time.time() - start_time:.4f}秒, 模型: {model}")
        return {"response": "抱歉，我暂时无法回答你的问题，请稍后再试。"}

@app.get("/")
async def root():
    return FileResponse(os.path.join("static", "index.html"))

@app.get("/models")
async def get_models():
    return {
        "models": [
            {"value": "deepseek", "label": "DeepSeek"},
            {"value": "qwen", "label": "千问"},
            {"value": "glm", "label": "智谱GLM"},
            {"value": "hunyuan", "label": "混元"}
        ]
    }