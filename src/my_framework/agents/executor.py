# File: src/my_framework/agents/executor.py

import re
from typing import List, Dict, Any
from pydantic import BaseModel

from .tools import BaseTool
from ..core.runnables import Runnable
from ..core.schemas import HumanMessage, AIMessage, SystemMessage
from ..models.base import BaseChatModel
from .utils import get_publication_ids_from_llm
from ..apps import rules

class AgentExecutor(BaseModel, Runnable[Dict[str, Any], str]):
    """The runtime for a ReAct-style agent."""
    llm: BaseChatModel
    tools: List[BaseTool]
    system_prompt: str | None = None
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
        article_title = input.get("article_title", "")
        article_body = input.get("article_body", "")
        tool_names = ", ".join([tool.name for tool in self.tools])
        tools_str = self._format_tools()

        intermediate_steps = ""

        # Use the custom system prompt if provided, otherwise use the default
        prompt_template = self.system_prompt or rules.DEFAULT_AGENT_PROMPT_TEMPLATE

        # Get the publication IDs based on the article's content using an LLM call
        publication_ids_to_select = get_publication_ids_from_llm(self.llm, article_title, article_body)
        input["publication_id_selections"] = publication_ids_to_select

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
                        observation = tool.run(input)
                    except Exception as e:
                        observation = f"Error executing tool {action_name}: {e}"
                else:
                    observation = f"Error: Tool '{action_name}' not found."

                # 5. Update scratchpad for the next loop
                intermediate_steps += llm_output + f"\nObservation: {observation}\n"
            else:
                # If the LLM output doesn't match the expected format,
                # treat the entire output as the final answer.
                return llm_output.strip()

        return "Agent stopped after reaching max iterations."