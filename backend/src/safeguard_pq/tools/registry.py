"""Tool registry: the callable APIs agents use to gather evidence.

Every tool is a plain, side-effect-free function with a JSON-schema parameter
description. The same registry is exposed over HTTP (``/api/v1/tools``) so
external agents, LLM function-calling loops, or analysts can call exactly the
functions the built-in agents use. Each agent call is recorded in the run
trace, which is what makes the assessment auditable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any


class ToolError(Exception):
    pass


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]
    summarize: Callable[[Any], str] = field(default=lambda r: _default_summary(r))
    online: bool = False
    category: str = "analysis"

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "online": self.online,
            "parameters": self.parameters,
        }


def _default_summary(result: Any) -> str:
    if isinstance(result, list):
        return f"{len(result)} item(s)"
    if isinstance(result, dict):
        keys = ", ".join(list(result)[:4])
        return f"object with {keys}"
    return str(result)[:80]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"unknown tool: {name}") from exc

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def call(self, name: str, /, **kwargs: Any) -> Any:
        tool = self.get(name)
        required = tool.parameters.get("required", [])
        missing = [r for r in required if r not in kwargs]
        if missing:
            raise ToolError(f"{name}: missing required argument(s): {', '.join(missing)}")
        allowed = set(tool.parameters.get("properties", {}))
        unknown = set(kwargs) - allowed
        if unknown:
            raise ToolError(f"{name}: unknown argument(s): {', '.join(sorted(unknown))}")
        return tool.func(**kwargs)


@lru_cache
def default_registry() -> ToolRegistry:
    from .builtin import register_builtin_tools

    reg = ToolRegistry()
    register_builtin_tools(reg)
    return reg
