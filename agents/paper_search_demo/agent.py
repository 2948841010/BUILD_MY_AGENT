import os
import asyncio
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

os.environ['DEEPSEEK_API_KEY'] = "sk-86bc0ca023294b4d94596861c70c6f45"



# Configure SSE params
sse_params = SseServerParams(
    url="http://47.92.93.30:50001/sse",  
)

toolset = MCPToolset(
    connection_params=SseServerParams(
        url="http://47.92.93.30:50001/sse",
    ),
)


use_model = "deepseek"

if use_model == "deepseek":
    model = LiteLlm(model="deepseek/deepseek-chat")

# Create agent
root_agent = Agent(
    name="mcp_sse_agent",
    model=model,
    instruction="You are an intelligent assistant capable of using external tools via MCP.",
    tools=[toolset]
)
