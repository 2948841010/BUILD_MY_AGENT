import os
import asyncio
import ssl
import httpx
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from typing import Any, Dict
import openai

# Set environment variables if needed
# 从环境变量读取API密钥，如果没有则使用默认值
os.environ['DEEPSEEK_API_KEY'] = os.getenv('DEEPSEEK_API_KEY', 'sk-your-deepseek-api-key-here')

# 解决SSL证书问题
# 方法1: 禁用SSL验证（仅用于开发环境）
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

# 方法2: 如果需要SSL验证，确保证书文件路径正确
try:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
except Exception as e:
    print(f"SSL配置警告: {e}")

# Configure SSE params
sse_params = SseServerParams(
    url="https://03593ce517feac573fdaafa6dcedef61.app-space.dplink.cc/sse?token=fdd0d45a3f224eaf8a3b56d706b61fed",  
)

toolset = MCPToolset(
    connection_params=SseServerParams(
        url="https://03593ce517feac573fdaafa6dcedef61.app-space.dplink.cc/sse?token=fdd0d45a3f224eaf8a3b56d706b61fed",
    ),
)


use_model = "deepseek"

if use_model == "deepseek":
    model = LiteLlm(model="deepseek/deepseek-chat")

# Create agent
root_agent = Agent(
    name="mcp_sse_agent",
    model=model,
    instruction="你是一个智能的GitHub仓库搜索和分析专家助手",
    tools=[toolset]
)
