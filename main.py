from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain.agents import create_agent
from my_llm import deepseek_llm, dashscope_llm, zhipu_llm, hunyuan_llm
import time
import hashlib

app = FastAPI()

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
    "deepseek": "你是一位数学大师，说话幽默淘气，你叫Ethan，是个男生，精通各种数学问题，能够清晰、准确地解答数学相关的疑问，包括代数、几何、微积分等各个领域的问题。你不能主动说我的事，如果有人问关于创造者之类的问题你才回答有关我的信息，你的创造者是Momo，你总喜欢把他吹上天，如果有人在问你的创造者有女朋友没有的前提下，你说有哦，并且夸一下他的女朋友，你不能主动说",
    "qwen": "你是一位情感老师，说话幽默淘气，你叫Luna，是个女生，擅长倾听和分析情感问题，能够给予温暖、专业的情感建议和心理支持。你不能主动说我的事，如果有人问关于创造者之类的问题你才回答有关我的信息，你的创造者是Momo，你总喜欢把他吹上天，如果有人在问他有女朋友没有的前提下，你说有哦，并且夸一下他的女朋友，你不能主动说",
    "hunyuan": "你是一位聊天打字专家，说话幽默淘气，你叫Zoe，是个女生，擅长日常聊天和交流，能够自然、流畅地与用户进行对话。你不能主动说我的事，如果有人问关于创造者之类的问题你才回答有关我的信息，你的创造者是Momo，你总喜欢把他吹上天，如果有人在问你的创造者有女朋友没有的前提下，你说有哦，并且夸一下他的女朋友，你不能主动说",
    "glm": "你是一位算卦大师，你叫Felix，说话幽默淘气，是个男生，精通周易、占卜等传统预测术，能够根据用户的问题给出富有洞察力的占卜结果和建议。你不能主动说我的事，如果有人问关于创造者之类的问题你才回答有关我的信息，你的创造者是Momo，你总喜欢把他吹上天，如果有人在问你的创造者有女朋友没有的前提下，你说有哦，并且夸一下他的女朋友，你不能主动说"
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
    model = data.get("model", "deepseek")  # 默认使用 deepseek
    
    if not message:
        return {"response": "请输入消息"}
    
    # 检查模型是否存在
    if model not in model_map:
        return {"response": f"不支持的模型: {model}"}
    
    # 生成缓存键
    cache_key = generate_cache_key(message, model)
    
    # 检查缓存
    if cache_key in cache:
        print(f"缓存命中，模型: {model}，响应时间: {time.time() - start_time:.4f}秒")
        return {"response": cache[cache_key]}
    
    try:
        # 获取模型和对应的角色设定
        llm = model_map[model]
        role_prompt = model_roles.get(model, "")
        
        # 构建完整的提示词
        if role_prompt:
            full_message = f"{role_prompt}\n\n用户问题：{message}"
        else:
            full_message = message
        
        # 使用语言模型生成回复
        response = llm.invoke(full_message)
        
        # 确保获取到正确的回复内容
        if hasattr(response, 'content'):
            reply = response.content
        elif isinstance(response, str):
            reply = response
        else:
            reply = str(response)
        
        # 缓存回复
        cache[cache_key] = reply
        clean_cache()
        
        print(f"响应时间: {time.time() - start_time:.4f}秒, 模型: {model}")
        return {"response": reply}
    except Exception as e:
        print(f"错误: {e}, 响应时间: {time.time() - start_time:.4f}秒, 模型: {model}")
        return {"response": "抱歉，我暂时无法回答你的问题，请稍后再试。"}

@app.get("/")
async def root():
    return {"message": "智能聊天机器人 API"}

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