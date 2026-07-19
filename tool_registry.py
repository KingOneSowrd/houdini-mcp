"""Typed registry used by the compact Houdini MCP tool surface.

The registry is deliberately independent of FastMCP and ``hou``.  It can be
queried before Houdini is running, while individual invokers may still relay
commands to the Houdini plug-in or call a bridge-local service such as OPUS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Type

from pydantic import BaseModel, ConfigDict, ValidationError


RiskLevel = Literal["low", "medium", "high"]
Availability = Callable[[], tuple[bool, Optional[str]]]
Invoker = Callable[[Dict[str, Any]], Dict[str, Any]]


class ToolArguments(BaseModel):
    """Base class for catalog argument models.

    Rejecting extra fields catches misspelled arguments before a command can
    mutate a Houdini scene.
    """

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class DocRef:
    """A portable reference to SideFX documentation.

    ``archive`` and ``entry`` are paths relative to the Houdini help root;
    absolute paths are resolved at runtime and are never stored in metadata.
    """

    kind: Literal["hom", "node", "concept"]
    archive: str
    entry: str
    official_url: str
    symbol: Optional[str] = None
    title: Optional[str] = None

    def as_dict(self, houdini_version: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "kind": self.kind,
            "local_ref": f"{self.archive}:{self.entry}",
            "official_url": self.official_url,
        }
        if self.symbol:
            result["symbol"] = self.symbol
        if self.title:
            result["title"] = self.title
        if houdini_version:
            result["houdini_version"] = houdini_version
        return result


@dataclass
class ToolSpec:
    name: str
    category: str
    description: str
    arguments_model: Type[ToolArguments]
    invoke: Invoker
    docs: List[DocRef]
    keywords: tuple[str, ...] = ()
    mutating: bool = False
    undoable: bool = False
    risk: RiskLevel = "low"
    examples: List[Dict[str, Any]] = field(default_factory=list)
    availability: Optional[Availability] = None

    def availability_status(self) -> tuple[bool, Optional[str]]:
        if self.availability is None:
            return True, None
        try:
            return self.availability()
        except Exception as exc:  # availability must never break discovery
            return False, f"Availability check failed: {exc}"

    def summary(self, houdini_version: Optional[str] = None) -> Dict[str, Any]:
        available, reason = self.availability_status()
        result: Dict[str, Any] = {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "mutating": self.mutating,
            "undoable": self.undoable,
            "risk": self.risk,
            "available": available,
            "official_docs": [doc.as_dict(houdini_version) for doc in self.docs[:2]],
        }
        if reason:
            result["unavailable_reason"] = reason
        return result

    def schema(self, houdini_version: Optional[str] = None) -> Dict[str, Any]:
        result = self.summary(houdini_version)
        result["input_schema"] = self.arguments_model.model_json_schema()
        result["examples"] = self.examples
        result["official_docs"] = [doc.as_dict(houdini_version) for doc in self.docs]
        return result


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        if not spec.docs:
            raise ValueError(f"Tool must cite SideFX documentation: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return sorted(self._tools)

    def specs(self) -> Iterable[ToolSpec]:
        return self._tools.values()

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        mutating: Optional[bool] = None,
        risk: Optional[RiskLevel] = None,
        available: Optional[bool] = None,
        offset: int = 0,
        limit: int = 10,
        houdini_version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        words = [word for word in query.strip().lower().split() if word]
        ranked: List[tuple[int, str, ToolSpec]] = []
        for spec in self._tools.values():
            if category and spec.category.lower() != category.lower():
                continue
            if mutating is not None and spec.mutating != mutating:
                continue
            if risk is not None and spec.risk != risk:
                continue
            spec_available, _ = spec.availability_status()
            if available is not None and spec_available != available:
                continue

            name = spec.name.lower()
            keywords = " ".join(spec.keywords).lower()
            description = spec.description.lower()
            category_text = spec.category.lower()
            haystack = " ".join((name, keywords, description, category_text))
            if words and not all(word in haystack for word in words):
                continue
            needle = " ".join(words)
            if not words:
                score = 0
            elif name == needle:
                score = 100
            elif name.startswith(needle):
                score = 80
            elif needle in name:
                score = 60
            elif needle in keywords:
                score = 40
            else:
                score = 20
            ranked.append((score, name, spec))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        capped = max(1, min(int(limit), 50))
        start = max(0, int(offset))
        return [spec.summary(houdini_version) for _, _, spec in ranked[start:start + capped]]

    def invoke(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        allow_unsafe: bool = False,
    ) -> Dict[str, Any]:
        spec = self.get(name)
        if spec is None:
            return {
                "status": "error",
                "message": f"Unknown catalog tool: {name}",
                "origin": "tool_registry",
            }
        available, reason = spec.availability_status()
        if not available:
            return {
                "status": "error",
                "message": reason or f"Tool is unavailable: {name}",
                "origin": "availability",
            }
        if spec.risk == "high" and not allow_unsafe:
            return {
                "status": "error",
                "message": (
                    f"Tool '{name}' is high risk. Retry with allow_unsafe=true "
                    "only when arbitrary Houdini code execution is required."
                ),
                "origin": "risk_policy",
            }
        try:
            validated = spec.arguments_model.model_validate(arguments or {})
        except ValidationError as exc:
            return {
                "status": "error",
                "message": "Invalid tool arguments",
                "origin": "validation",
                "details": exc.errors(include_url=False),
            }
        try:
            result = spec.invoke(validated.model_dump(exclude_none=True, by_alias=True))
        except Exception as exc:
            return {
                "status": "error",
                "message": str(exc),
                "origin": "tool_registry",
            }
        if isinstance(result, dict) and result.get("status") in {"success", "error"}:
            if result.get("status") == "error":
                result.setdefault("official_docs", [doc.as_dict() for doc in spec.docs])
            return result
        return {"status": "success", "result": result}
