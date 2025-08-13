"""
NexusAgent Symbolic Regression Agent

This module defines the main NexusAgent and its sub-agents for symbolic regression tasks.
The agent orchestrates the entire workflow from data analysis to final report generation.
"""

import os
import sys
from pathlib import Path
# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google.adk import Agent
from google.adk.agents import LlmAgent

from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import SequentialAgent

from Nexusagent_SR.prompt.agent_prompt import (
    research_agent_prompt,
    prior_agent_prompt,
    symbolic_agent_prompt,
    summarize_agent_prompt,
)
from Nexusagent_SR.tool.agent_tool import *


model = os.getenv("MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini if MODEL env var is not set


research_agent = Agent(
    name="ResearchAgent",
    model=LiteLlm(model=model),
    description="Use <generate_data_description_tool> to generate data description and save to a variable with the key `data_description`",
    tools=[
        generate_data_description_tool,
    ],
    instruction=research_agent_prompt,
    output_key="data_description"
)

prior_agent = Agent(
    name="PriorAgent",
    model=LiteLlm(model=model),
    description="Use <set_unary_operators_tool> to set the unary operators.",
    tools=[
        set_unary_operators_tool
    ],
    instruction=prior_agent_prompt,
)


symbolic_agent = Agent(
    name="SymbolicAgent",
    model=LiteLlm(model=model),
    description="Use <run_symbolic_tool_pysr> to run symbolic regression with the csv_path,the csv_path is saved in the variable with the key `csv_path`",
    instruction=symbolic_agent_prompt,
    tools=[
        run_symbolic_tool_pysr,
    ],
    output_key="symbolic_result"
)


summarize_agent = Agent(
    name="SummarizeAgent",
    model=LiteLlm(model=model),
    description="Use <write_summarize_report_tool> to write the summarize report",
    instruction=summarize_agent_prompt,
    tools=[
        summarize_report_tool,
    ],
    output_key="summarize_report"
)


sr_iteration_agent = SequentialAgent(
    name="SRIterationAgent",
    description="Execute a single iteration: set configuration -> run symbolic regression -> generate summary -> refine the summarize report",
    sub_agents=[prior_agent, symbolic_agent, summarize_agent],
)



rootagent = SequentialAgent(
    name="NexusAgent",
    description="Execute the symbolic regression workflow: research -> SR iteration",
    sub_agents=[research_agent,sr_iteration_agent],
)