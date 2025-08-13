import os
import nest_asyncio
from dotenv import load_dotenv
from dp.agent.adapter.adk import CalculationMCPToolset
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

# Load credentials
nest_asyncio.apply()
load_dotenv()

# === Bohrium config ===
BOHRIUM_EXECUTOR = {
   "type": "dispatcher",
   "machine": {
       "batch_type": "Bohrium",
       "context_type": "Bohrium",
       "remote_profile": {
           "email": os.getenv("BOHRIUM_EMAIL"),
           "password": os.getenv("BOHRIUM_PASSWORD"),
           "program_id": int(os.getenv("BOHRIUM_PROJECT_ID")),
           "input_data": {
               "image_name": "registry.dp.tech/dptech/dp/native/prod-435364/agents:0.1.0",
               "job_type": "container",
               "platform": "ali",
               "scass_type": "c32_m128_cpu"
           }
       }
   },
   "resources":{
       "group_size": 1
   }
}
#BOHRIUM_EXECUTOR_MAP = {
#   "build_structure": BOHRIUM_EXECUTOR["enthalpy"],
#   "predict_thermoelectric_properties": BOHRIUM_EXECUTOR["enthalpy"],
#}

BOHRIUM_STORAGE = {
    "type": "bohrium",
    "username": os.getenv("BOHRIUM_EMAIL"),
    "password": os.getenv("BOHRIUM_PASSWORD"),
    "project_id": int(os.getenv("BOHRIUM_PROJECT_ID"))
}

# === Server config ===
server_url = "https://thermoelectricmcp000-uuid1750905361.app-space.dplink.cc/sse?token=d00381812368432b874f1e58b9cc2d6d"
#server_url = "https://db346ccb62d491029b590bbbf0f5c412.app-space.dplink.cc/sse?token=b019009078d647848a702b6c33f281a2"
session_service = InMemorySessionService()

# === MCP toolset ===
mcp_tools = CalculationMCPToolset(
    connection_params=SseServerParams(url=server_url),
    storage=BOHRIUM_STORAGE,
    executor=BOHRIUM_EXECUTOR
    #executor_map=BOHRIUM_EXECUTOR_MAP
)

# === Define agent ===
root_agent = LlmAgent(
    model=LiteLlm(model="azure/gpt-4o"),
    name="gpt_thermoelectric_agent",
    description="Helps with Deep Potential calculations and material thermoelectronic properties.",
    instruction="""
        Use MCP tools when structure input is provided. Otherwise, respond naturally to user queries.
        If users did not provide necessary parameters of the functions, ALWAYS use default settings.
    """,
    tools=[mcp_tools]
)

