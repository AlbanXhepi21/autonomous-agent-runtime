"""A small, safe arithmetic calculator tool."""

import ast
import math
import operator
from typing import Any

from app.tools.base import Tool, ToolInputError


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
        return (
            "Evaluate exactly one arithmetic expression using numeric literals, "
            "parentheses, and +, -, *, /, //, %, or **. Submit only the expression "
            "(for example, '(7 * 133) - (7 * 101)'); do not include labels, units, "
            "currency symbols, variable assignments, or an equals sign."
        )

    @property
    def arguments_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": (
                        "One arithmetic expression only, such as '7 * 101' or "
                        "'((931 - 707) / 707) * 100'. Do not include '=' or prose."
                    ),
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        }

    async def execute(self, **arguments: Any) -> str:
        expression = arguments.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            raise ToolInputError(
                "Calculator requires one non-empty arithmetic expression."
            )
        if len(expression) > 256:
            raise ToolInputError("Calculator expressions must be 256 characters or fewer.")

        try:
            parsed = ast.parse(expression, mode="eval")
            result = self._evaluate(parsed.body)
        except (ArithmeticError, SyntaxError, TypeError, ValueError) as error:
            raise ToolInputError(
                "Calculator accepts one expression with numbers, parentheses, and "
                "+, -, *, /, //, %, or ** only. Submit the expression without labels, "
                "units, currency symbols, variable assignments, or '='."
            ) from error
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
