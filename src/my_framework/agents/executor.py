# File: src/my_framework/agents/executor.py

import re
from typing import List, Dict, Any
from pydantic import BaseModel # <--- ADD THIS IMPORT

from .tools import BaseTool
from ..core.runnables import Runnable
from ..core.schemas import HumanMessage, AIMessage, SystemMessage
from ..models.base import BaseChatModel

DEFAULT_AGENT_PROMPT_TEMPLATE = """
You are a helpful assistant that has access to the following tools.
Respond to the user's query by reasoning about the problem and using the tools
to find the answer.

Here are the available tools:
{tools}

Use the following format for your response:

Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

User Query: {input}
Agent Scratchpad: {agent_scratchpad}
"""

# --- THE FIX IS ON THE LINE BELOW ---
class AgentExecutor(BaseModel, Runnable[Dict[str, Any], str]):
    """The runtime for a ReAct-style agent."""
    llm: BaseChatModel
    tools: List[BaseTool]
    system_prompt: str | None = None # <-- ADDED THIS FIELD
    max_iterations: int = 5

    class Config:
        arbitrary_types_allowed = True

    def _format_tools(self) -> str:
        """Format the list of tools for the prompt."""
        return "\n".join(
            [f"- {tool.name}: {tool.description}" for tool in self.tools]
        )

    def _get_tool_by_name(self, name: str) -> BaseTool | None:
        """Find a tool in the list by its name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def invoke(self, input: Dict[str, Any], config=None) -> str:
        """Executes the agent's reasoning loop."""
        user_input = input.get("input", "")
        tool_names = ", ".join([tool.name for tool in self.tools])
        tools_str = self._format_tools()
        
        intermediate_steps = ""
        
        # Use the custom system prompt if provided, otherwise use the default
        prompt_template = self.system_prompt or DEFAULT_AGENT_PROMPT_TEMPLATE
        
        for i in range(self.max_iterations):
            # 1. Format the prompt
            prompt_content = prompt_template.format(
                tools=tools_str,
                tool_names=tool_names,
                input=user_input,
                agent_scratchpad=intermediate_steps
            )
            
            # 2. Call the LLM
            messages = [
                SystemMessage(content="You are an AI agent."), # A generic role
                HumanMessage(content=prompt_content)
            ]
            response = self.llm.invoke(messages)
            llm_output = response.content
            
            # 3. Parse the output
            final_answer_match = re.search(r"Final Answer:\s*(.*)", llm_output, re.DOTALL)
            action_match = re.search(r"Action:\s*(.*?)\nAction Input:\s*(.*)", llm_output, re.DOTALL)

            if final_answer_match:
                return final_answer_match.group(1).strip()

            if action_match:
                action_name = action_match.group(1).strip()
                action_input = action_match.group(2).strip()

                # 4. Dispatch to the tool
                tool = self._get_tool_by_name(action_name)
                if tool:
                    try:
                        observation = tool.run(action_input)
                    except Exception as e:
                        observation = f"Error executing tool {action_name}: {e}"
                else:
                    observation = f"Error: Tool '{action_name}' not found."

                # 5. Update scratchpad for the next loop
                intermediate_steps += llm_output + f"\nObservation: {observation}\n"
            else:
                return "Agent failed to produce a valid action or final answer."

        return "Agent stopped after reaching max iterations."