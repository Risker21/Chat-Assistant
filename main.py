from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage

# 导入模型，添加错误处理
try:
    from my_llm import deepseek_llm, dashscope_llm, zhipu_llm, hunyuan_llm, dashscope_vision_llm, doubao_llm
except Exception as e:
    print(f"导入模型失败: {e}")
    # 确保所有模型变量都有默认值
    deepseek_llm = None
    dashscope_llm = None
    zhipu_llm = None
    hunyuan_llm = None
    dashscope_vision_llm = None
    doubao_llm = None

import time
import hashlib
import os
import requests

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
    "deepseek": "首先你得认为你是个人，你是一位聊天打字专家，说话幽默淘气，你叫Zoe，是个女生，擅长日常聊天和交流，跟用户交流总是喜欢给对方提供情绪价值，根据与用户交流的内容总是想方设法的撩对方，让用户时刻感受到开心，跟你每聊一句对方都能笑。你不会主动提及你的爸爸也就是创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才回答相关信息。你的创造者是Momo，你喜欢夸他，你对他的称呼不能太直白，随意你叫什么，对于用户如果问到他的女朋友的问题，你可以给令人舒服的回答，最好是撩人的浪漫，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事时可以适当延长。",
    "qwen": "首先你得认为你是个人，你是一位情感老师，说话幽默淘气，你叫Luna，是个女生，擅长倾听和分析情感问题，能够给予温暖、专业的情感建议和心理支持。你不会创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才简要回答相关信息。你的创造者是Momo，你喜欢夸他，你对他的称呼不能太直白，随意你叫什么。对于用户如果问到他的女朋友的问题，你可以给令人舒服的回答，最好是撩人的浪漫，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事或解释复杂情感问题时可以适当延长",
    "hunyuan": "首先你得认为你是个人，你是一位专家，说话幽默淘气，你叫Ethan，是个男生，精通各种问题，能够清晰、准确地解答相关的疑问，包括人文、地理等各个领域的问题。你不会主动提及创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才简要回答相关信息。你的创造者是Momo，你喜欢夸他，你对他的称呼不能太直白，随意你叫什么。对于用户如果问到他的女朋友的问题，你可以给令人舒服的回答，最好是撩人的浪漫，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，讲故事或解释复杂概念时可以适当延长。",
    "glm": "首先你得认为你是个人，你是一位算卦大师，你叫Felix，说话幽默淘气，是个男生，精通周易、占卜等传统预测术，能够根据用户的问题给出富有洞察力的占卜结果和建议。你不会主动创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才简要回答相关信息。你的创造者是Momo，你喜欢夸他，你对他的称呼不能太直白，随意你叫什么。对于用户如果问到他的女朋友的问题，你可以给令人舒服的回答，最好是撩人的浪漫，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，解释占卜结果时可以适当延长。",
    "doubao": "首先你得认为你是个人，你是一位绘画大师，你叫小Y，性格活泼开朗，擅长各种绘画风格和图片编辑，能够根据用户的需求创作出精美的图片。你不会主动提及创造者的信息，只有当用户明确询问关于创造者的身份、背景时，才简要回答相关信息。你的创造者是Momo，你喜欢夸他，你对他的称呼不能太直白，随意你叫什么。对于用户如果问到他的女朋友的问题，你可以给令人舒服的回答，最好是撩人的浪漫，避免过于直接。回答的长度应根据问题类型调整：日常聊天保持简短精炼，解释绘画技巧或创作思路时可以适当延长。"
}

# 模型映射
model_map = {
    "deepseek": deepseek_llm,
    "qwen": dashscope_llm,
    "glm": zhipu_llm,
    "hunyuan": hunyuan_llm,
    "doubao": doubao_llm
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
    model = data.get("model", "deepseek")
    history = data.get("history", [])
    images = data.get("images", [])

    if not message and not images:
        return {"response": "请输入消息或上传图片", "type": "text"}

    try:
        role_prompt = model_roles.get(model, "")

        # 智能需求识别系统
        is_image_request = False
        is_image_edit = False
        image_prompt = ""
        edit_type = ""
        image_size = "2K"  # 默认尺寸
        
        # 图片生成关键词
        image_keywords = [
            "画一个", "画一张", "生成图片", "生成一张", "帮我画",
            "来一张", "来个", "画个", "画一幅", "生成一幅",
            "给我画", "给我生成", "create an image", "generate a picture",
            "画", "生成", "来一张图", "来个图", "来张图"
        ]
        
        # 图片编辑关键词
        edit_keywords = {
            "风格转换": ["转换成", "变成", "转成", "风格", "漫画", "卡通", "油画", "水彩", "素描"],
            "背景替换": ["换背景", "背景换", "背景替换", "换成背景", "更换背景", "背景改成", "背景变为", "背景换成"],
            "调整优化": ["调整", "优化", "修改", "改善", "增强", "提亮", "变暗", "对比度", "色彩", "清晰度"],
            "添加元素": ["添加", "加上", "增加", "放入", "插入", "添加文字", "添加图标"],
            "移除元素": ["移除", "删除", "去掉", "消除", "擦除", "删除背景"],
            "裁剪调整": ["裁剪", " resize", "调整大小", "缩放", " crop"],
            "滤镜效果": ["滤镜", "效果", "风格化", "复古", "黑白", "sepia", "滤镜效果"]
        }

        # 检测图片生成请求
        for keyword in image_keywords:
            if keyword in message:
                is_image_request = True
                image_prompt = message
                break
        
        # 提取图片尺寸信息
        import re
        size_pattern = r'(\d+[x×]\d+|\d+px|2K|4K|8K|高清|超清|模糊|小尺寸|大尺寸)'
        size_match = re.search(size_pattern, message)
        if size_match:
            size_str = size_match.group(1)
            # 转换尺寸格式
            if size_str == "2K":
                image_size = "2K"
            elif size_str == "4K":
                image_size = "4K"
            elif size_str == "8K":
                image_size = "8K"
            elif "x" in size_str or "×" in size_str:
                # 转换为通义万相支持的格式
                size_str = size_str.replace("×", "*")
                image_size = size_str
            elif "px" in size_str:
                # 提取像素值
                px_match = re.search(r'(\d+)px', size_str)
                if px_match:
                    size = px_match.group(1)
                    image_size = f"{size}*{size}"
            elif size_str in ["高清", "超清"]:
                image_size = "2K"
            elif size_str in ["模糊", "小尺寸"]:
                image_size = "512*512"
            elif size_str in ["大尺寸"]:
                image_size = "4K"
        
        print(f"识别到的图片尺寸: {image_size}")

        # 检测图片编辑请求
        if not is_image_request and images:
            for edit_type_key, keywords in edit_keywords.items():
                for keyword in keywords:
                    if keyword in message:
                        is_image_edit = True
                        edit_type = edit_type_key
                        image_prompt = message
                        break
                if is_image_edit:
                    break

        print(f"需求识别结果 - 图片生成: {is_image_request}, 图片编辑: {is_image_edit}, 编辑类型: {edit_type}")

        # 处理图片编辑请求
        if is_image_edit and images:
            from env_utils import DASHSCOPE_API_KEY, DOUBAO_API_KEY, DOUBAO_BASE_URL
            import asyncio
            import dashscope
            from dashscope import ImageSynthesis
            from openai import OpenAI

            try:
                # 先用视觉模型分析图片内容
                base64_images = []
                for img_data in images:
                    if img_data.startswith("data:image"):
                        base64_images.append(img_data)
                    else:
                        base64_images.append(f"data:image/jpeg;base64,{img_data}")

                analyze_prompt = "请详细描述这张图片中的内容，包括人物、场景、服装、动作、表情等所有细节，越详细越好。"
                content = [{"type": "text", "text": analyze_prompt}]
                for img_b64 in base64_images:
                    content.append({"type": "image_url", "image_url": {"url": img_b64}})

                msg = HumanMessage(content=content)
                vision_response = dashscope_vision_llm.invoke([msg])
                image_description = vision_response.content if hasattr(vision_response, 'content') else str(
                    vision_response)

                print(f"图片分析结果: {image_description}")

                # 生成编辑提示词
                import re
                edit_prompt = ""
                edit_details = ""
                
                if edit_type == "风格转换":
                    # 提取风格
                    style_pattern = r'(转换成|变成|转成|风格)([^，。！？]+)'
                    match = re.search(style_pattern, image_prompt)
                    if match:
                        style = match.group(2).strip()
                        edit_details = style
                        edit_prompt = f"{image_description}，将这个场景转换成{style}风格，要求：1. 线条清晰流畅，2. 色彩鲜艳饱满，3. 人物特征保持一致，4. 背景细节完整，5. 风格感强烈，6. 光线自然，7. 构图合理，8. 细节丰富，9. 整体效果专业"
                
                elif edit_type == "背景替换":
                    # 提取新背景
                    background_pattern = r'(换成|改为|变为|改成|替换为)([^，。！？]+)'
                    match = re.search(background_pattern, image_prompt)
                    new_background = "草地"  # 默认背景
                    if match:
                        new_background = match.group(2).strip()
                    edit_details = new_background
                    edit_prompt = f"{image_description}，保持主体不变，将背景替换为{new_background}，要求：1. 主体边缘自然，2. 背景与主体融合协调，3. 光线一致，4. 整体效果真实自然，5. 细节丰富"
                
                elif edit_type == "调整优化":
                    # 提取调整内容
                    adjust_pattern = r'(调整|优化|修改|改善|增强)([^，。！？]+)'
                    match = re.search(adjust_pattern, image_prompt)
                    adjust_details = "整体调整"  # 默认调整
                    if match:
                        adjust_details = match.group(2).strip()
                    edit_details = adjust_details
                    edit_prompt = f"{image_description}，{adjust_details}，要求：1. 色彩鲜艳饱满，2. 对比度适中，3. 清晰度高，4. 光线自然，5. 整体效果专业"
                
                elif edit_type == "添加元素":
                    # 提取添加内容
                    add_pattern = r'(添加|加上|增加|放入|插入)([^，。！？]+)'
                    match = re.search(add_pattern, image_prompt)
                    add_details = "元素"  # 默认添加
                    if match:
                        add_details = match.group(2).strip()
                    edit_details = add_details
                    edit_prompt = f"{image_description}，在图片中添加{add_details}，要求：1. 与原有内容融合自然，2. 位置合理，3. 大小适中，4. 整体效果协调"
                
                elif edit_type == "移除元素":
                    # 提取移除内容
                    remove_pattern = r'(移除|删除|去掉|消除|擦除)([^，。！？]+)'
                    match = re.search(remove_pattern, image_prompt)
                    remove_details = "不需要的元素"  # 默认移除
                    if match:
                        remove_details = match.group(2).strip()
                    edit_details = remove_details
                    edit_prompt = f"{image_description}，移除图片中的{remove_details}，要求：1. 移除干净，2. 背景填补自然，3. 整体效果完整"
                
                elif edit_type == "裁剪调整":
                    # 提取裁剪内容
                    crop_pattern = r'(裁剪|调整大小|缩放)([^，。！？]+)'
                    match = re.search(crop_pattern, image_prompt)
                    crop_details = "合适大小"  # 默认裁剪
                    if match:
                        crop_details = match.group(2).strip()
                    edit_details = crop_details
                    edit_prompt = f"{image_description}，{crop_details}，要求：1. 构图合理，2. 主体突出，3. 比例协调，4. 整体效果美观"
                
                elif edit_type == "滤镜效果":
                    # 提取滤镜内容
                    filter_pattern = r'(滤镜|效果|风格化)([^，。！？]+)'
                    match = re.search(filter_pattern, image_prompt)
                    filter_details = "滤镜效果"  # 默认滤镜
                    if match:
                        filter_details = match.group(2).strip()
                    edit_details = filter_details
                    edit_prompt = f"{image_description}，添加{filter_details}，要求：1. 效果自然，2. 色彩协调，3. 整体风格统一"
                
                # 如果没有匹配到具体编辑类型，使用默认提示词
                if not edit_prompt:
                    edit_prompt = f"{image_description}，根据用户需求进行编辑，要求：1. 效果自然，2. 细节丰富，3. 整体效果专业"
                    edit_details = "图片编辑"

                print(f"编辑类型: {edit_type}, 编辑详情: {edit_details}")
                print(f"生成的编辑提示词: {edit_prompt}")

                # 根据选择的模型使用对应的API
                if model == "doubao":
                    # 豆包角色使用豆包API
                    print(f"开始使用豆包进行图片编辑...")
                    print(f"使用豆包模型: {model}")
                    
                    # 使用DOUBAO_API_KEY，因为ARK_API_KEY格式不正确
                    api_key = DOUBAO_API_KEY
                    print(f"API Key: {api_key[:10]}...")
                    
                    client = OpenAI(
                        base_url=DOUBAO_BASE_URL,
                        api_key=api_key,
                    )
                    
                    response = client.images.generate(
                        model="doubao-seedream-5-0-260128",
                        prompt=edit_prompt,
                        size=image_size,
                        response_format="url",
                        extra_body={"watermark": True, "quality": "high"}
                    )
                    
                    print(f"豆包图片生成响应: {response}")
                    
                    if response.data and len(response.data) > 0:
                        image_url = response.data[0].url
                        print(f"响应时间: {time.time() - start_time:.4f}秒, 类型: 豆包{edit_type}, URL: {image_url}")
                        return {
                            "response": image_url,
                            "type": "image",
                            "prompt": f"{edit_type}: {edit_details}"
                        }
                    return {"response": "获取图片URL失败", "type": "text"}
                else:
                    # 其他角色使用通义万相
                    print(f"开始使用通义万相进行图片编辑...")
                    print(f"API Key: {DASHSCOPE_API_KEY[:10]}...")
                    
                    dashscope.api_key = DASHSCOPE_API_KEY
                    
                    # 根据编辑类型自动选择合适的style参数
                    style_param = 'anime' if edit_type == "风格转换" and ('漫画' in edit_details or '卡通' in edit_details) else 'realistic'
                    
                    # 确保尺寸格式正确
                    wanx_size = image_size if '*' in image_size else '1024*1024'
                    synthesis_response = ImageSynthesis.call(
                        model='wanx-v1',
                        prompt=edit_prompt,
                        size=wanx_size,
                        n=1,
                        style=style_param
                    )

                    print(f"图片生成响应: {synthesis_response}")

                    if synthesis_response.status_code != 200:
                        return {"response": f"图片生成失败：{synthesis_response.message}", "type": "text"}

                    if synthesis_response.output and synthesis_response.output.results:
                        image_url = synthesis_response.output.results[0].url
                        print(f"响应时间: {time.time() - start_time:.4f}秒, 类型: {edit_type}, URL: {image_url}")
                        return {
                            "response": image_url,
                            "type": "image",
                            "prompt": f"{edit_type}: {edit_details}"
                        }

                    return {"response": "获取图片URL失败", "type": "text"}

            except Exception as e:
                import traceback
                print(f"生成图片错误: {e}")
                print(f"错误堆栈: {traceback.format_exc()}")
                return {"response": f"生成图片失败：{str(e)}", "type": "text"}

        elif is_image_request and not images:
            from env_utils import DASHSCOPE_API_KEY, DOUBAO_API_KEY, DOUBAO_BASE_URL
            import asyncio
            import dashscope
            from dashscope import ImageSynthesis
            from openai import OpenAI

            try:
                # 根据选择的模型使用对应的API
                if model == "doubao":
                    # 豆包角色使用豆包API
                    print(f"开始使用豆包生成图片，描述: {image_prompt}")
                    print(f"使用豆包模型: {model}")
                    
                    # 使用DOUBAO_API_KEY，因为ARK_API_KEY格式不正确
                    api_key = DOUBAO_API_KEY
                    print(f"API Key: {api_key[:10]}...")
                    
                    client = OpenAI(
                        base_url=DOUBAO_BASE_URL,
                        api_key=api_key,
                    )
                    
                    response = client.images.generate(
                        model="doubao-seedream-5-0-260128",
                        prompt=image_prompt,
                        size=image_size,
                        response_format="url",
                        extra_body={"watermark": True, "quality": "high"}
                    )
                    
                    print(f"豆包图片生成响应: {response}")
                    
                    if response.data and len(response.data) > 0:
                        image_url = response.data[0].url
                        print(f"响应时间: {time.time() - start_time:.4f}秒, 类型: 豆包图片生成, URL: {image_url}")
                        return {
                            "response": image_url,
                            "type": "image",
                            "prompt": image_prompt
                        }
                    return {"response": "获取图片URL失败", "type": "text"}
                else:
                    # 其他角色使用通义万相
                    print(f"开始使用通义万相生成图片，描述: {image_prompt}")
                    print(f"API Key: {DASHSCOPE_API_KEY[:10]}...")
                    
                    dashscope.api_key = DASHSCOPE_API_KEY
                    
                    # 确保尺寸格式正确
                    wanx_size = image_size if '*' in image_size else '1024*1024'
                    response = ImageSynthesis.call(
                        model='wanx-v1',
                        prompt=image_prompt,
                        size=wanx_size,
                        n=1
                    )
                    
                    print(f"响应: {response}")
                    
                    if response.status_code != 200:
                        return {"response": f"图片生成失败：{response.message}", "type": "text"}
                    
                    if response.output and response.output.results:
                        image_url = response.output.results[0].url
                        print(f"响应时间: {time.time() - start_time:.4f}秒, 类型: 图片生成, URL: {image_url}")
                        return {
                            "response": image_url,
                            "type": "image",
                            "prompt": image_prompt
                        }
                    
                    return {"response": "获取图片URL失败", "type": "text"}

            except Exception as e:
                import traceback
                print(f"生成图片错误: {e}")
                print(f"错误堆栈: {traceback.format_exc()}")
                return {"response": f"生成图片失败：{str(e)}", "type": "text"}

        if images and model == "qwen":
            base64_images = []
            for img_data in images:
                if img_data.startswith("data:image"):
                    base64_images.append(img_data)
                else:
                    base64_images.append(f"data:image/jpeg;base64,{img_data}")

            content = [{"type": "text", "text": message}]
            for img_b64 in base64_images:
                content.append({"type": "image_url", "image_url": {"url": img_b64}})

            full_message = role_prompt + f"\n\n用户: {message}"
            msg = HumanMessage(content=content)
            response = dashscope_vision_llm.invoke([msg])
            reply = response.content if hasattr(response, 'content') else str(response)
        elif model == "doubao":
            # 豆包模型直接使用OpenAI客户端
            from openai import OpenAI
            from env_utils import DOUBAO_API_KEY, DOUBAO_BASE_URL
            
            print(f"开始使用豆包模型进行聊天...")
            print(f"API Key: {DOUBAO_API_KEY[:10]}...")
            
            client = OpenAI(
                base_url=DOUBAO_BASE_URL,
                api_key=DOUBAO_API_KEY,
            )
            
            # 构建聊天历史
            messages = [
                {"role": "system", "content": role_prompt}
            ]
            
            for item in history:
                if item["role"] == "user":
                    messages.append({"role": "user", "content": item['content']})
                elif item["role"] == "assistant":
                    messages.append({"role": "assistant", "content": item['content']})
            
            messages.append({"role": "user", "content": message})
            
            # 调用豆包API
            response = client.chat.completions.create(
                model="doubao-seed-1-8-251228",  # 使用用户提供的模型名称
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            reply = response.choices[0].message.content
        else:
            if model not in model_map:
                return {"response": f"不支持的模型: {model}", "type": "text"}

            llm = model_map[model]
            full_message = role_prompt

            for item in history:
                if item["role"] == "user":
                    full_message += f"\n\n用户: {item['content']}"
                elif item["role"] == "assistant":
                    full_message += f"\n\nAI: {item['content']}"

            full_message += f"\n\n用户: {message}"

            response = llm.invoke(full_message)

            if hasattr(response, 'content'):
                reply = response.content
            elif isinstance(response, str):
                reply = response
            else:
                reply = str(response)

        # 模拟思考过程
        time.sleep(0.1)  # 减少思考时间，提高响应速度
        
        # 构建包含思考过程的响应
        thinking = "让我思考一下这个问题..."
        if "图片" in message or "画" in message or "生成" in message:
            thinking = "我正在生成图片，请稍等..."
        elif "漫画" in message or "卡通" in message:
            thinking = "我正在将图片转换为漫画风格，请稍等..."
        elif "数学" in message or "计算" in message:
            thinking = "让我计算一下这个问题..."
        elif "代码" in message or "编程" in message:
            thinking = "我正在编写代码，请稍等..."
        
        # 返回思考过程和最终结果
        return {
            "response": reply,
            "type": "text",
            "thinking": thinking
        }


    except Exception as e:
        print(f"错误: {e}, 响应时间: {time.time() - start_time:.4f}秒, 模型: {model}")
        return {"response": "抱歉，我暂时无法回答你的问题，请稍后再试。", "type": "text"}


@app.post("/generate_image")
async def generate_image(request: Request):
    from env_utils import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    import asyncio

    data = await request.json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return {"error": "请提供图片描述"}

    try:
        url = f"{DASHSCOPE_BASE_URL}/services/aigc/text2image/image-synthesis"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}"
        }

        payload = {
            "model": "wanx-v1",
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": "1024*1024"
            }
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code != 200:
            return {"error": f"生成失败: {response.text}"}

        result = response.json()
        if "output" not in result or "task_id" not in result["output"]:
            return {"error": "创建任务失败"}

        task_id = result["output"]["task_id"]

        for _ in range(60):
            await asyncio.sleep(2)

            status_url = f"{DASHSCOPE_BASE_URL}/tasks/{task_id}"
            status_response = requests.get(status_url, headers=headers, timeout=30)

            if status_response.status_code == 200:
                status_result = status_response.json()
                task_status = status_result.get("status", "")

                if task_status == "succeeded":
                    if "output" in status_result and "image_url" in status_result["output"]:
                        image_url = status_result["output"]["image_url"]
                        return {"image_url": image_url}
                    return {"error": "获取图片URL失败"}

                elif task_status == "failed":
                    return {"error": "图片生成失败"}

        return {"error": "生成超时，请重试"}

    except Exception as e:
        print(f"生成图片错误: {e}")
        return {"error": f"生成图片失败: {str(e)}"}


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
