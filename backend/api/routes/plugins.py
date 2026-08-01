# coding: utf-8
"""
api/routes/plugins.py

Plugin and Tool API endpoints.

v1.5 endpoints:
    GET  /api/plugins          List all registered plugins with metadata.
    POST /api/plugins/execute  Execute a plugin by name.

Design notes:
    - Uses the live agent ToolRegistry (same instance as the runtime).
    - Built-in tools are excluded from the plugin listing.
    - Response schema is forward-compatible with v1.6 /api/tools.
    - Execute endpoint uses 'tool' + 'arguments' naming (future-proof).
      'plugin' + 'input' aliases accepted for backward compatibility.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agent.services.agent import get_agent_runtime
from backend.agent.tools.plugin_adapter import PluginAdapter
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/plugins", tags=["Plugins"])


# ---------------------------------------------------------------------------
# Built-in tool names — excluded from plugin listing
# These are registered directly in agent/services/agent.py
# ---------------------------------------------------------------------------

_BUILTIN_TOOLS = {"calculator", "datetime", "filesystem"}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PluginInfo(BaseModel):
    name:        str
    version:     str
    description: str
    healthy:     bool
    built_in:    bool
    loaded:      bool


class PluginListResponse(BaseModel):
    total:   int
    plugins: list[PluginInfo]


class ExecuteRequest(BaseModel):
    # Future-proof naming
    tool:      Optional[str]            = Field(None, description="Tool name to execute.")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Tool arguments.")

    # Backward-compatible aliases
    plugin: Optional[str]            = Field(None, description="Alias for 'tool'.")
    input:  Optional[Dict[str, Any]] = Field(None, description="Alias for 'arguments'.")

    def resolved_tool(self) -> str:
        name = self.tool or self.plugin
        if not name:
            raise ValueError("Either 'tool' or 'plugin' must be provided.")
        return name

    def resolved_arguments(self) -> Dict[str, Any]:
        return self.arguments or self.input or {}


class ExecuteResponse(BaseModel):
    tool:    str
    success: bool
    result:  Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=PluginListResponse,
    summary="List installed plugins",
    description="Returns all plugin-provided tools registered in the runtime.",
)
def list_plugins() -> PluginListResponse:
    """
    Return all plugin-provided tools with metadata.

    Built-in tools (calculator, datetime, filesystem) are excluded.
    Only tools loaded via the Plugin SDK are returned here.
    """
    runtime  = get_agent_runtime()
    registry = runtime.registry

    plugins: list[PluginInfo] = []

    for name in registry.list_tools():
        tool     = registry.get(name)
        is_builtin = name in _BUILTIN_TOOLS

        # Only include plugin-provided tools in this endpoint
        if is_builtin:
            continue

        # Determine version — PluginAdapter exposes the underlying plugin
        version = "1.0.0"
        if isinstance(tool, PluginAdapter):
            version = tool._plugin.version

        healthy = True
        try:
            if isinstance(tool, PluginAdapter):
                healthy = tool._plugin.health_check()
        except Exception:
            healthy = False

        plugins.append(PluginInfo(
            name        = name,
            version     = version,
            description = tool.description,
            healthy     = healthy,
            built_in    = False,
            loaded      = True,
        ))

    logger.info("[Plugins API] Listed %d plugin(s).", len(plugins))

    return PluginListResponse(
        total   = len(plugins),
        plugins = plugins,
    )


@router.get(
    "/all",
    summary="List all tools",
    description="Returns all tools including built-ins and plugins.",
)
def list_all_tools():
    """
    Return every tool registered in the runtime.
    Built-ins and plugins both included.
    Forward-looking — this becomes /api/tools in v1.6.
    """
    runtime  = get_agent_runtime()
    registry = runtime.registry

    tools = []

    for name in registry.list_tools():
        tool       = registry.get(name)
        is_builtin = name in _BUILTIN_TOOLS

        version = "built-in"
        if isinstance(tool, PluginAdapter):
            version = tool._plugin.version

        healthy = True
        try:
            if isinstance(tool, PluginAdapter):
                healthy = tool._plugin.health_check()
        except Exception:
            healthy = False

        tools.append({
            "name":        name,
            "version":     version,
            "description": tool.description,
            "healthy":     healthy,
            "built_in":    is_builtin,
            "loaded":      True,
        })

    return {"total": len(tools), "tools": tools}


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Execute a plugin",
    description="Execute any registered plugin by name with provided arguments.",
)
def execute_plugin(request: ExecuteRequest) -> ExecuteResponse:
    """
    Execute a registered plugin tool.

    Accepts both naming conventions:
        { "tool": "weather", "arguments": { "location": "Tokyo" } }
        { "plugin": "weather", "input": { "location": "Tokyo" } }
    """
    try:
        tool_name = request.resolved_tool()
        arguments = request.resolved_arguments()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    runtime  = get_agent_runtime()
    registry = runtime.registry

    if not registry.has_tool(tool_name):
        available = registry.list_tools()
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available: {available}",
        )

    try:
        result = registry.execute_structured(tool_name, **arguments)
        logger.info("[Plugins API] Executed '%s' successfully.", tool_name)
        return ExecuteResponse(
            tool    = tool_name,
            success = True,
            result  = result,
        )

    except Exception as exc:
        logger.error("[Plugins API] Execution failed for '%s': %s", tool_name, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Execution failed: {exc}",
        )