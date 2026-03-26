"""
LangChain / LangGraph + AgentID Example
========================================
This example shows how to wrap LangChain tools with AgentID so every
tool call is verified against policy and logged to the audit trail.

Run:
    pip install agentid langchain langchain-openai
    python examples/langchain_example.py
"""

import asyncio
import os
from agentid import AgentIDClient
from agentid.middleware.langchain import agentid_langchain_middleware

# ── 1. Bootstrap the AgentID client ──────────────────────────────────────────

client = AgentIDClient(
    base_url=os.getenv("AGENTID_URL", "http://localhost:8000"),
    agent_id=os.getenv("AGENTID_AGENT_ID", "your-agent-id"),
    api_key=os.getenv("AGENTID_API_KEY", "agid_your_key"),
    ttl_minutes=15,
)

# ── 2. Define your LangChain tools ────────────────────────────────────────────

try:
    from langchain.tools import BaseTool

    class FakeEmailTool(BaseTool):
        name: str = "send_email"
        description: str = "Send an email to a recipient"

        def _run(self, recipient: str, subject: str, body: str) -> str:
            # In production, this would call Gmail / SendGrid / etc.
            print(f"[FakeEmailTool] Sending email to {recipient}: {subject}")
            return f"Email sent to {recipient}"

        async def _arun(self, recipient: str, subject: str, body: str) -> str:
            return self._run(recipient, subject, body)

    class FakeSearchTool(BaseTool):
        name: str = "web_search"
        description: str = "Search the web for information"

        def _run(self, query: str) -> str:
            print(f"[FakeSearchTool] Searching: {query}")
            return f"Search results for: {query}"

        async def _arun(self, query: str) -> str:
            return self._run(query)

    raw_tools = [FakeEmailTool(), FakeSearchTool()]

except ImportError:
    print("langchain not installed — showing SDK usage only")
    raw_tools = []


# ── 3. Wrap tools with AgentID ────────────────────────────────────────────────

async def main():
    async with client:
        # Wrap all tools — this injects identity + audit logging automatically
        tools = agentid_langchain_middleware(
            tools=raw_tools,
            client=client,
            enforce_policy=True,  # deny if policy check fails
        )

        print(f"Registered {len(tools)} AgentID-protected tools")

        # Show the agent's current token
        token = await client.get_token()
        print(f"Agent JWT (truncated): {token[:60]}...")

        # Manually verify an action before doing it
        allowed, reason = await client.verify("email:send", "user@example.com")
        print(f"Policy check — email:send: allowed={allowed}, reason={reason}")

        # Log a custom action
        await client.log_action(
            action="email:send",
            resource="user@example.com",
            result="allowed",
            prompt_snippet="Send a welcome email to the new user",
            tool_called="send_email",
            result_summary="Email delivered successfully",
            cost_usd=0.002,
            duration_ms=342,
        )
        print("Action logged to audit trail")

        # Get agent info
        info = await client.get_info()
        print(f"Agent: {info.name} | Owner: {info.owner_id} | Status: {info.status}")

        # Example: use with a real LangChain agent (requires langchain-openai)
        # from langchain_openai import ChatOpenAI
        # from langchain.agents import create_react_agent, AgentExecutor
        # from langchain import hub
        #
        # llm = ChatOpenAI(model="gpt-4o-mini")
        # prompt = hub.pull("hwchase17/react")
        # agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        # executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        # result = executor.invoke({"input": "Send a welcome email to pedro@example.com"})
        # print(result)


if __name__ == "__main__":
    asyncio.run(main())
