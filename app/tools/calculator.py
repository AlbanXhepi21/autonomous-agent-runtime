"""A small, safe arithmetic calculator tool."""

import ast
import math
import operator
from typing import Any

from app.tools.base import Tool


class CalculatorTool(Tool):
    """Evaluate simple arithmetic without using unrestricted eval."""

    _binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _unary_operators = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a simple arithmetic expression."

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        expression = arguments.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("calculator requires a non-empty expression string")
        if len(expression) > 256:
            raise ValueError("calculator expression is too long")

        try:
            parsed = ast.parse(expression, mode="eval")
            result = self._evaluate(parsed.body)
        except (ArithmeticError, SyntaxError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid calculator expression: {expression}") from error
        return str(result)

    def _evaluate(self, node: ast.expr) -> int | float:
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
            and math.isfinite(node.value)
        ):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_operators:
            return self._unary_operators[type(node.op)](self._evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in self._binary_operators:
            left = self._evaluate(node.left)
            right = self._evaluate(node.right)
            if isinstance(node.op, ast.Pow):
                if not isinstance(right, int) or abs(right) > 100:
                    raise ValueError("exponent must be an integer between -100 and 100")
                if abs(left) > 1e100:
                    raise ValueError("base is too large for exponentiation")
            result = self._binary_operators[type(node.op)](left, right)
            if not isinstance(result, (int, float)) or isinstance(result, bool):
                raise ValueError("result must be a finite real number")
            if isinstance(result, float) and not math.isfinite(result):
                raise ValueError("result is not finite")
            if isinstance(result, int) and result.bit_length() > 4096:
                raise ValueError("result is too large")
            return result
        raise ValueError("only numeric arithmetic is allowed")
