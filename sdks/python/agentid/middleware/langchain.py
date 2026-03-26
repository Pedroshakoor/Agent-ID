"""
LangChain / LangGraph middleware for AgentID.

Usage:
    from agentid import AgentIDClient
    from agentid.middleware.langchain import AgentIDToolWrapper

    client = AgentIDClient(
        base_url="http://localhost:8000",
        agent_id="your-agent-id",
        api_key="agid_your_key",
    )

    # Wrap any LangChain tool to auto-inject auth headers + log every call
    wrapped_tool = AgentIDToolWrapper(tool=my_tool, client=client)

    # Use in any LangChain agent as a drop-in replacement
    agent = create_react_agent(llm=llm, tools=[wrapped_tool])
"""

from __future__ import annotations

import time
from typing import Any

from agentid.client import AgentIDClient


class AgentIDToolWrapper:
    """
    Wraps a LangChain BaseTool to automatically:
    - Inject the AgentID JWT into calls that need auth headers
    - Log every tool invocation to the AgentID audit trail
    - Enforce policy before execution (optional)

    Compatible with LangChain 0.2+ and LangGraph.
    """

    def __init__(
        self,
        tool: Any,
        client: AgentIDClient,
        resource_prefix: str | None = None,
        enforce_policy: bool = False,
        log_inputs: bool = True,
    ):
        self._tool = tool
        self._client = client
        self._resource_prefix = resource_prefix or f"tool:{tool.name}"
        self._enforce_policy = enforce_policy
        self._log_inputs = log_inputs

        # Proxy all LangChain tool attributes
        self.name = tool.name
        self.description = tool.description
        self.args_schema = getattr(tool, "args_schema", None)

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        action = f"tool:{self.name}"
        resource = self._resource_prefix
        start = time.perf_counter()

        # Optional pre-flight policy check
        if self._enforce_policy:
            allowed, reason = await self._client.verify(action, resource)
            if not allowed:
                await self._client.log_action(
                    action=action,
                    resource=resource,
                    result="denied",
                    result_summary=reason,
                )
                raise PermissionError(f"AgentID policy denied '{action}': {reason}")

        # Execute the original tool
        error_msg: str | None = None
        result: Any = None
        try:
            if hasattr(self._tool, "_arun"):
                result = await self._tool._arun(*args, **kwargs)
            else:
                result = self._tool._run(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            snippet = str(kwargs or args)[:512] if self._log_inputs else None
            await self._client.log_action(
                action=action,
                resource=resource,
                result="error" if error_msg else "allowed",
                prompt_snippet=snippet,
                tool_called=self.name,
                result_summary=error_msg or str(result)[:256],
                duration_ms=duration_ms,
            )

        return result

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Sync fallback — runs async in a new event loop."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(*args, **kwargs))

    # LangChain compatibility shim
    def invoke(self, input: Any, config: Any = None) -> Any:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun_from_invoke(input))

    async def ainvoke(self, input: Any, config: Any = None) -> Any:
        return await self._arun_from_invoke(input)

    async def _arun_from_invoke(self, input: Any) -> Any:
        if isinstance(input, dict):
            return await self._arun(**input)
        return await self._arun(input)


def agentid_langchain_middleware(
    tools: list[Any],
    client: AgentIDClient,
    enforce_policy: bool = False,
) -> list[AgentIDToolWrapper]:
    """
    Wrap a list of LangChain tools with AgentID identity + audit logging.

    Args:
        tools: List of LangChain BaseTool instances
        client: Initialized AgentIDClient
        enforce_policy: If True, deny tool calls that fail policy checks

    Returns:
        List of wrapped tools (drop-in replacement)

    Example:
        tools = agentid_langchain_middleware(
            tools=[search_tool, email_tool],
            client=agentid_client,
            enforce_policy=True,
        )
        agent = create_react_agent(llm=llm, tools=tools)
    """
    return [
        AgentIDToolWrapper(tool=tool, client=client, enforce_policy=enforce_policy)
        for tool in tools
    ]
