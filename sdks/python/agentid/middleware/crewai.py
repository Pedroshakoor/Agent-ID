"""
CrewAI middleware for AgentID.

Usage:
    from agentid import AgentIDClient
    from agentid.middleware.crewai import AgentIDCrewMixin

    class MyResearchAgent(AgentIDCrewMixin, Agent):
        agentid_client = AgentIDClient(
            base_url="http://localhost:8000",
            agent_id="your-agent-id",
            api_key="agid_your_key",
        )

    # Or use the standalone task wrapper:
    from agentid.middleware.crewai import agentid_task_callback

    task = Task(
        description="Research the topic",
        callback=agentid_task_callback(client, action="research:web"),
    )
"""

from __future__ import annotations

import time
from typing import Any


class AgentIDCrewMixin:
    """
    Mixin for CrewAI Agent classes. Adds automatic action logging
    for every task execution.

    Add this mixin before Agent in your MRO:
        class MyAgent(AgentIDCrewMixin, Agent): ...
    """

    agentid_client: Any = None  # Set on class or instance

    def execute_task(self, task: Any, context: Any = None, tools: list = None) -> str:  # type: ignore
        if self.agentid_client is None:
            # Fall through without logging if client not configured
            return super().execute_task(task, context, tools)  # type: ignore

        import asyncio

        action = f"crewai:task:{getattr(task, 'description', 'unknown')[:64]}"
        start = time.perf_counter()
        error_msg: str | None = None
        result: str = ""

        try:
            result = super().execute_task(task, context, tools)  # type: ignore
            return result
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        self.agentid_client.log_action(
                            action=action,
                            result="error" if error_msg else "allowed",
                            result_summary=error_msg or result[:256],
                            duration_ms=duration_ms,
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.agentid_client.log_action(
                            action=action,
                            result="error" if error_msg else "allowed",
                            result_summary=error_msg or result[:256],
                            duration_ms=duration_ms,
                        )
                    )
            except Exception:
                pass  # Never let audit logging break the agent


def agentid_task_callback(client: Any, action: str = "crewai:task") -> Any:
    """
    Returns a CrewAI task callback that logs the result to AgentID.

    Usage:
        task = Task(
            description="...",
            callback=agentid_task_callback(client, action="research:web"),
        )
    """

    def callback(output: Any) -> None:
        import asyncio
        try:
            result_str = str(output)[:512]
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    client.log_action(
                        action=action,
                        result="allowed",
                        result_summary=result_str,
                    )
                )
            else:
                loop.run_until_complete(
                    client.log_action(
                        action=action,
                        result="allowed",
                        result_summary=result_str,
                    )
                )
        except Exception:
            pass

    return callback
