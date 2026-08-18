"""OpenAI implementation of the provider-neutral LLM interface."""

import json
from typing import Any

from openai import AsyncOpenAI

from app.agent.models import AgentAction
from app.llm.base import LLMClient


class OpenAIClient(LLMClient):
    """Translate OpenAI function calls into provider-neutral agent actions."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def choose_action(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
    ) -> AgentAction:
        """Return one action selected through native function calling."""

        response = await self._client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context)},
            ],
            tools=self._function_definitions(context),
            tool_choice="required",
            parallel_tool_calls=False,
        )
        function_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if function_call is None:
            raise ValueError("OpenAI did not return an agent function call.")

        try:
            arguments = json.loads(function_call.arguments)
        except json.JSONDecodeError as error:
            raise ValueError("OpenAI returned invalid function arguments.") from error
        if not isinstance(arguments, dict):
            raise ValueError("OpenAI function arguments must be a JSON object.")

        return self._to_agent_action(function_call.name, arguments)

    def _function_definitions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Build strict native function definitions from the runtime context."""

        functions = [
            self._tool_function(tool)
            for tool in context.get("available_tools", [])
            if isinstance(tool, dict)
        ]
        skill_names = [
            skill["name"]
            for skill in context.get("available_skills", [])
            if isinstance(skill, dict) and isinstance(skill.get("name"), str)
        ]
        if skill_names:
            functions.append(self._load_skill_function(skill_names))
        agent_names = [
            agent["name"]
            for agent in context.get("available_specialist_agents", [])
            if isinstance(agent, dict) and isinstance(agent.get("name"), str)
        ]
        if agent_names:
            functions.append(self._delegate_function(agent_names))
            runtime_status = context.get("runtime_status")
            max_parallel = (
                runtime_status.get("max_parallel_subagents", 1)
                if isinstance(runtime_status, dict)
                else 1
            )
            if isinstance(max_parallel, int) and max_parallel >= 2:
                functions.append(self._delegate_parallel_function(agent_names, max_parallel))
        functions.append(self._finish_function())
        return functions

    @staticmethod
    def _tool_function(tool: dict[str, Any]) -> dict[str, Any]:
        name = tool.get("name")
        description = tool.get("description")
        schema = tool.get("arguments_schema")
        if not isinstance(name, str) or not isinstance(description, str) or not isinstance(schema, dict):
            raise ValueError("Tool definitions must include name, description, and arguments_schema.")

        return {
            "type": "function",
            "name": f"tool_{name}",
            "description": description,
            "parameters": OpenAIClient._schema_with_reasoning(schema),
            "strict": True,
        }

    @staticmethod
    def _load_skill_function(skill_names: list[str]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": "load_skill",
            "description": "Load the full instructions for one available skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "enum": skill_names},
                    "reasoning_summary": OpenAIClient._reasoning_schema(),
                },
                "required": ["skill_name", "reasoning_summary"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    @staticmethod
    def _finish_function() -> dict[str, Any]:
        return {
            "type": "function",
            "name": "finish",
            "description": "Finish the task when the available evidence is sufficient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "final_answer": {"type": "string"},
                    "reasoning_summary": OpenAIClient._reasoning_schema(),
                },
                "required": ["final_answer", "reasoning_summary"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    @staticmethod
    def _delegate_function(agent_names: list[str]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": "delegate",
            "description": "Request bounded help from one available specialist agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "enum": agent_names},
                    "objective": {"type": "string"},
                    "context": {"type": ["string", "null"]},
                    "constraints": {"type": ["string", "null"]},
                    "expected_output": {"type": ["string", "null"]},
                    "reasoning_summary": OpenAIClient._reasoning_schema(),
                },
                "required": ["agent_name", "objective", "reasoning_summary"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    @staticmethod
    def _delegate_parallel_function(agent_names: list[str], max_parallel: int) -> dict[str, Any]:
        item_properties = {
            "agent_name": {"type": "string", "enum": agent_names},
            "objective": {"type": "string"},
            "context": {"type": ["string", "null"]},
            "constraints": {"type": ["string", "null"]},
            "expected_output": {"type": ["string", "null"]},
        }
        return {
            "type": "function",
            "name": "delegate_parallel",
            "description": "Delegate independent bounded objectives concurrently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delegations": {
                        "type": "array", "minItems": 2, "maxItems": max_parallel,
                        "items": {
                            "type": "object", "properties": item_properties,
                            "required": ["agent_name", "objective"],
                            "additionalProperties": False,
                        },
                    },
                    "reasoning_summary": OpenAIClient._reasoning_schema(),
                },
                "required": ["delegations", "reasoning_summary"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    @staticmethod
    def _schema_with_reasoning(schema: dict[str, Any]) -> dict[str, Any]:
        properties = dict(schema.get("properties", {}))
        properties["reasoning_summary"] = OpenAIClient._reasoning_schema()
        required = list(schema.get("required", []))
        if "reasoning_summary" not in required:
            required.append("reasoning_summary")
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    @staticmethod
    def _reasoning_schema() -> dict[str, str]:
        return {
            "type": "string",
            "description": "Short operational explanation; do not reveal private reasoning.",
        }

    @staticmethod
    def _to_agent_action(name: str, arguments: dict[str, Any]) -> AgentAction:
        reasoning_summary = arguments.pop("reasoning_summary", None)
        if not isinstance(reasoning_summary, str):
            raise ValueError("OpenAI function call is missing reasoning_summary.")

        if name.startswith("tool_"):
            return AgentAction(
                action_type="use_tool",
                reasoning_summary=reasoning_summary,
                tool_name=name.removeprefix("tool_"),
                tool_arguments=arguments,
            )
        if name == "load_skill":
            return AgentAction(
                action_type="load_skill",
                reasoning_summary=reasoning_summary,
                skill_name=arguments.get("skill_name"),
            )
        if name == "finish":
            return AgentAction(
                action_type="finish",
                reasoning_summary=reasoning_summary,
                final_answer=arguments.get("final_answer"),
            )
        if name == "delegate":
            return AgentAction(
                action_type="delegate",
                reasoning_summary=reasoning_summary,
                agent_name=arguments.get("agent_name"),
                objective=arguments.get("objective"),
                context=arguments.get("context"),
                constraints=arguments.get("constraints"),
                expected_output=arguments.get("expected_output"),
            )
        if name == "delegate_parallel":
            return AgentAction(
                action_type="delegate_parallel",
                reasoning_summary=reasoning_summary,
                delegations=arguments.get("delegations", []),
            )
        raise ValueError(f"OpenAI returned an unknown agent function: {name}")
