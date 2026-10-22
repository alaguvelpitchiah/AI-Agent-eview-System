"""Example tool-using agent: plan -> calculator tool call -> respond."""
from __future__ import annotations

import ast
import operator
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ...integration.config_utils import apply_overrides, config_version, load_yaml
from ...integration.tracing import MISSING, EventRecorder

STAGES = ("plan", "respond")
TOOLS = ("calculator",)
_PACKAGE = Path(__file__).parent
_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
Number = Union[int, float]


class ToolError(Exception):
    """The calculator tool could not evaluate the expression."""


def safe_eval(expression: str, cfg: Dict[str, Any]) -> Number:
    """Evaluate +, -, *, /, ** and parentheses on numbers. Nothing else is allowed."""
    if len(expression) > cfg["planner"]["max_expression_length"]:
        raise ToolError("Expression is too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError("Invalid expression") from exc

    def ev(node: ast.AST) -> Number:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = ev(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > cfg["tool"]["max_exponent"]:
                raise ToolError("Exponent is too large")
            try:
                return _BINARY[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise ToolError("Division by zero") from exc
        raise ToolError("Unsupported expression")

    value = ev(tree)
    value = round(value, cfg["tool"]["precision"])
    return int(value) if float(value).is_integer() else value


def plan_expression(question: str, cfg: Dict[str, Any]) -> Dict[str, Optional[str]]:
    text = question.lower()
    for phrase, symbol in sorted(cfg["operators"].items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(phrase)}\b", f" {symbol} ", text)
    text = re.sub(r"[^0-9.+\-*/()\s]", " ", text)
    expression = re.sub(r"\s+", " ", text).strip()
    has_number = re.search(r"\d", expression) is not None
    has_operator = re.search(r"[+\-*/]", expression) is not None
    return {"expression": expression if has_number and has_operator else None}


class CalculatorAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config if config is not None else load_yaml(_PACKAGE / "config.yaml")

    @property
    def version(self) -> str:
        return config_version(self.config)

    def run(
        self,
        question: str,
        stage_overrides: Optional[Dict[str, Any]] = None,
        tool_overrides: Optional[Dict[str, Any]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        recorder: Optional[EventRecorder] = None,
    ) -> Dict[str, Any]:
        stage_overrides = stage_overrides or {}
        tool_overrides = tool_overrides or {}
        cfg = apply_overrides(self.config, config_overrides)
        version = config_version(cfg)
        recorder = recorder or EventRecorder()
        recorder.version = version

        plan = recorder.step(
            "plan", lambda: plan_expression(question, cfg),
            input={"question": question}, override=stage_overrides.get("plan", MISSING),
        )
        expression = plan.get("expression")

        result: Optional[Number] = None
        if expression is not None:
            result = recorder.step(
                "calculator", lambda: safe_eval(expression, cfg), kind="tool_call",
                input={"expression": expression}, override=tool_overrides.get("calculator", MISSING),
            )

        reply = recorder.step(
            "respond", lambda: self._respond(expression, result, cfg),
            input={"expression": expression, "result": result}, override=stage_overrides.get("respond", MISSING),
        )
        return {"expression": expression, "result": result, "answer": reply["answer"], "config_version": version}

    @staticmethod
    def _respond(expression: Optional[str], result: Optional[Number], cfg: Dict[str, Any]) -> Dict[str, str]:
        if expression is None or result is None:
            return {"answer": cfg["response"]["fallback_message"]}
        return {"answer": cfg["response"]["template"].format(result=result)}
