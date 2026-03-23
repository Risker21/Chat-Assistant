# 智能聊天机器人

一个基于 FastAPI 和多种大语言模型的智能聊天机器人。

## 功能特点

- 支持多种大语言模型：DeepSeek、千问、智谱GLM、混元
- 不同模型有不同的角色设定
- 简单的缓存机制，提高响应速度
- RESTful API 接口
- 支持 CORS 跨域请求

## 技术栈

- Python 3.10+
- FastAPI
- LangChain
- 多种大语言模型 API

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件，添加以下内容：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

ZHIPU_API_KEY=your_api_key_here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

HUNYUAN_API_KEY=your_api_key_here
HUNYUAN_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
```

### 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 部署到 Vercel

### 步骤 1：准备代码

1. 确保你的代码已经提交到 GitHub 仓库
2. 确保 `vercel.json` 文件存在
3. 确保 `requirements.txt` 文件包含所有必要的依赖

### 步骤 2：配置 Vercel

1. 登录 Vercel 控制台
2. 点击 "Add New" -> "Project"
3. 选择你的 GitHub 仓库
4. 点击 "Import"
5. 在 "Environment Variables" 部分添加以下环境变量：
   - DEEPSEEK_API_KEY
   - DEEPSEEK_BASE_URL
   - DASHSCOPE_API_KEY
   - DASHSCOPE_BASE_URL
   - ZHIPU_API_KEY
   - ZHIPU_BASE_URL
   - HUNYUAN_API_KEY
   - HUNYUAN_BASE_URL
6. 点击 "Deploy"

### 步骤 3：访问部署后的应用

部署完成后，Vercel 会提供一个 URL，你可以通过这个 URL 访问你的应用。

## API 接口

### POST /chat

发送聊天消息

**请求体**：
```json
{
  "message": "你好",
  "model": "deepseek"
}
```

**响应**：
```json
{
  "response": "你好！我是 Ethan，一位数学大师。有什么数学问题可以问我吗？"
}
```

### GET /models

获取支持的模型列表

**响应**：
```json
{
  "models": [
    {"value": "deepseek", "label": "DeepSeek"},
    {"value": "qwen", "label": "千问"},
    {"value": "glm", "label": "智谱GLM"},
    {"value": "hunyuan", "label": "混元"}
  ]
}
```

### GET /

健康检查接口

**响应**：
```json
{
  "message": "智能聊天机器人 API"
}
```

## 注意事项

- 请不要将 API 密钥提交到版本控制系统
- 定期轮换 API 密钥以确保安全
- 在生产环境中，建议设置具体的 CORS 来源，而不是使用通配符
- 部署到 Vercel 时，确保在 Vercel 控制台中正确设置环境变量# 智能聊天机器人

一个基于 FastAPI 和多种大语言模型的智能聊天机器人。

## 功能特点

- 支持多种大语言模型：DeepSeek、千问、智谱GLM、混元
- 不同模型有不同的角色设定
- 简单的缓存机制，提高响应速度
- RESTful API 接口
- 支持 CORS 跨域请求

## 技术栈

- Python 3.10+
- FastAPI
- LangChain
- 多种大语言模型 API

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件，添加以下内容：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

ZHIPU_API_KEY=your_api_key_here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

HUNYUAN_API_KEY=your_api_key_here
HUNYUAN_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
```

### 启动服务

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 部署到 Vercel

### 步骤 1：准备代码

1. 确保你的代码已经提交到 GitHub 仓库
2. 确保 `vercel.json` 文件存在
3. 确保 `requirements.txt` 文件包含所有必要的依赖

### 步骤 2：配置 Vercel

1. 登录 Vercel 控制台
2. 点击 "Add New" -> "Project"
3. 选择你的 GitHub 仓库
4. 点击 "Import"
5. 在 "Environment Variables" 部分添加以下环境变量：
   - DEEPSEEK_API_KEY
   - DEEPSEEK_BASE_URL
   - DASHSCOPE_API_KEY
   - DASHSCOPE_BASE_URL
   - ZHIPU_API_KEY
   - ZHIPU_BASE_URL
   - HUNYUAN_API_KEY
   - HUNYUAN_BASE_URL
6. 点击 "Deploy"

### 步骤 3：访问部署后的应用

部署完成后，Vercel 会提供一个 URL，你可以通过这个 URL 访问你的应用。

## API 接口

### POST /chat

发送聊天消息

**请求体**：
```json
{
  "message": "你好",
  "model": "deepseek"
}
```

**响应**：
```json
{
  "response": "你好！我是 Ethan，一位数学大师。有什么数学问题可以问我吗？"
}
```

### GET /models

获取支持的模型列表

**响应**：
```json
{
  "models": [
    {"value": "deepseek", "label": "DeepSeek"},
    {"value": "qwen", "label": "千问"},
    {"value": "glm", "label": "智谱GLM"},
    {"value": "hunyuan", "label": "混元"}
  ]
}
```

### GET /

健康检查接口

**响应**：
```json
{
  "message": "智能聊天机器人 API"
}
```

## 注意事项

- 请不要将 API 密钥提交到版本控制系统
- 定期轮换 API 密钥以确保安全
- 在生产环境中，建议设置具体的 CORS 来源，而不是使用通配符
- 部署到 Vercel 时，确保在 Vercel 控制台中正确设置环境变量