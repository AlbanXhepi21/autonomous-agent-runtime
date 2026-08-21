"""OpenAI implementation of the provider-neutral LLM interface."""

import json
from typing import Any

from openai import AsyncOpenAI

from app.agent.models import AgentAction
from app.llm.base import LLMClient, LLMDecision, LLMUsage


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
        """Compatibility action-only provider interface."""

        return (await self.choose_decision(system_prompt=system_prompt, context=context)).action

    async def choose_decision(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
    ) -> LLMDecision:
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

        usage = getattr(response, "usage", None)
        input_details = getattr(usage, "input_tokens_details", None)
        output_details = getattr(usage, "output_tokens_details", None)
        return LLMDecision(
            action=self._to_agent_action(function_call.name, arguments), model=getattr(response, "model", None) or self._model, provider="openai",
            usage=LLMUsage(
                input_tokens=getattr(usage, "input_tokens", None), output_tokens=getattr(usage, "output_tokens", None),
                cached_input_tokens=getattr(input_details, "cached_tokens", None),
                cache_write_tokens=getattr(input_details, "cache_write_tokens", None),
                reasoning_tokens=getattr(output_details, "reasoning_tokens", None),
            ) if usage is not None else None,
        )

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
            # A few bounded runtime tools accept a deliberately free-form object
            # (for example a typed report payload). OpenAI strict mode cannot
            # represent an unconstrained object; runtime validation still applies.
            "strict": OpenAIClient._strict_compatible(schema),
        }

    @staticmethod
    def _strict_compatible(schema: Any) -> bool:
        """Return whether a tool schema can satisfy OpenAI strict JSON Schema rules."""

        if not isinstance(schema, dict):
            return True
        value_type = schema.get("type")
        types = {value_type} if isinstance(value_type, str) else set(value_type) if isinstance(value_type, list) else set()
        if "object" in types:
            properties = schema.get("properties")
            if not isinstance(properties, dict) or schema.get("additionalProperties") is not False:
                return False
            return all(OpenAIClient._strict_compatible(value) for value in properties.values())
        if "array" in types:
            items = schema.get("items")
            return isinstance(items, dict) and OpenAIClient._strict_compatible(items)
        return True

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
                "required": ["agent_name", "objective", "context", "constraints", "expected_output", "reasoning_summary"],
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
                            "required": ["agent_name", "objective", "context", "constraints", "expected_output"],
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
        originally_required = set(schema.get("required", []))
        for name, definition in list(properties.items()):
            if name not in originally_required and name != "reasoning_summary":
                properties[name] = OpenAIClient._nullable_property(definition)
        return {
            "type": "object",
            "properties": properties,
            # OpenAI strict function schemas require every declared property. Optional
            # runtime arguments are represented as nullable and normalized away below.
            "required": list(properties),
            "additionalProperties": False,
        }

    @staticmethod
    def _nullable_property(definition: Any) -> Any:
        """Make an optional flat tool argument valid in OpenAI strict mode."""

        if not isinstance(definition, dict):
            return definition
        nullable = dict(definition)
        value_type = nullable.get("type")
        if isinstance(value_type, str):
            nullable["type"] = [value_type, "null"]
        elif isinstance(value_type, list) and "null" not in value_type:
            nullable["type"] = [*value_type, "null"]
        return nullable

    @staticmethod
    def _reasoning_schema() -> dict[str, str]:
        return {
            "type": "string",
            "description": "Short operational explanation; do not reveal private reasoning.",
        }

    @staticmethod
    def _to_agent_action(name: str, arguments: dict[str, Any]) -> AgentAction:
        # This is public, optional trace metadata—not the model's private
        # reasoning.  Providers can occasionally omit it despite the strict
        # schema, and an omitted summary must not discard an otherwise valid
        # tool call or final answer.
        reasoning_summary = arguments.pop("reasoning_summary", "")
        if not isinstance(reasoning_summary, str):
            reasoning_summary = ""

        if name.startswith("tool_"):
            arguments = {key: value for key, value in arguments.items() if value is not None}
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
