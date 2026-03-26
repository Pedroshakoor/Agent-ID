"""
CrewAI + AgentID Example
========================
Shows two integration patterns:
  1. Task callback — logs every task result automatically
  2. AgentIDCrewMixin — full agent-level audit (if you subclass Agent)

Run:
    pip install agentid crewai
    python examples/crewai_example.py
"""

import asyncio
import os
from agentid import AgentIDClient
from agentid.middleware.crewai import agentid_task_callback

# ── AgentID client ────────────────────────────────────────────────────────────

client = AgentIDClient(
    base_url=os.getenv("AGENTID_URL", "http://localhost:8000"),
    agent_id=os.getenv("AGENTID_AGENT_ID", "your-agent-id"),
    api_key=os.getenv("AGENTID_API_KEY", "agid_your_key"),
)


# ── Pattern 1: Task callback (no subclassing needed) ─────────────────────────

async def run_with_callbacks():
    async with client:
        token = await client.get_token()
        print(f"Agent token issued: {token[:40]}...")

        try:
            from crewai import Agent, Task, Crew

            researcher = Agent(
                role="Research Analyst",
                goal="Gather market data on AI agent identity solutions",
                backstory="Expert at competitive analysis",
                verbose=False,
            )

            writer = Agent(
                role="Technical Writer",
                goal="Write a concise summary",
                backstory="Expert at distilling technical info",
                verbose=False,
            )

            research_task = Task(
                description="Research existing AI agent identity solutions",
                agent=researcher,
                expected_output="A list of solutions with pros and cons",
                callback=agentid_task_callback(client, action="research:web"),
            )

            write_task = Task(
                description="Write a 200-word summary of the findings",
                agent=writer,
                expected_output="A 200-word summary",
                callback=agentid_task_callback(client, action="write:summary"),
            )

            crew = Crew(
                agents=[researcher, writer],
                tasks=[research_task, write_task],
                verbose=False,
            )

            # result = crew.kickoff()
            # print(result)
            print("CrewAI crew configured with AgentID audit callbacks")

        except ImportError:
            print("crewai not installed — showing SDK usage only")

        # Manually log what the crew did
        await client.log_action(
            action="crew:kickoff",
            result="allowed",
            result_summary="Crew completed research + writing tasks",
            duration_ms=12400,
        )
        print("Crew execution logged to AgentID audit trail")


# ── Pattern 2: AgentIDCrewMixin (full subclass) ───────────────────────────────

def demo_mixin():
    try:
        from crewai import Agent
        from agentid.middleware.crewai import AgentIDCrewMixin

        class AuditedResearcher(AgentIDCrewMixin, Agent):
            """Every task.execute() is automatically logged via the mixin."""
            agentid_client = client

        print("AuditedResearcher class created — all task executions auto-logged")

    except ImportError:
        print("crewai not installed — skipping mixin demo")


if __name__ == "__main__":
    demo_mixin()
    asyncio.run(run_with_callbacks())
