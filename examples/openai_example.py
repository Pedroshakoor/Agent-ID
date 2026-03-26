"""
OpenAI Function Calling + AgentID Example
==========================================
Shows how to use AgentID with raw OpenAI function calling.
The "fake Gmail tool" checks the AgentID /verify endpoint before
granting access — exactly how external services should integrate.

Run:
    pip install agentid openai
    OPENAI_API_KEY=sk-... python examples/openai_example.py
"""

import asyncio
import json
import os
import time
from agentid import AgentIDClient

# ── AgentID client ────────────────────────────────────────────────────────────

client = AgentIDClient(
    base_url=os.getenv("AGENTID_URL", "http://localhost:8000"),
    agent_id=os.getenv("AGENTID_AGENT_ID", "your-agent-id"),
    api_key=os.getenv("AGENTID_API_KEY", "agid_your_key"),
)

# ── Fake Gmail tool (simulates an external service) ───────────────────────────

async def fake_gmail_send(to: str, subject: str, body: str, agent_token: str) -> dict:
    """
    Simulates an external Gmail API that verifies the AgentID token
    before performing any action.

    In a real integration, YOUR external service calls /v1/verify
    with the agent's token before granting access.
    """
    import httpx

    agentid_url = os.getenv("AGENTID_URL", "http://localhost:8000")

    # External service verifies the token
    async with httpx.AsyncClient() as http:
        verify_resp = await http.post(
            f"{agentid_url}/v1/verify",
            json={"action": "email:send", "resource": f"email:{to}"},
            headers={"Authorization": f"Bearer {agent_token}"},
        )

    if verify_resp.status_code != 200:
        return {"error": "Verification failed", "status": "denied"}

    result = verify_resp.json()
    if not result["allowed"]:
        return {
            "error": f"AgentID policy denied: {result['reason']}",
            "status": "denied",
        }

    # Token verified + policy allows → perform the action
    print(f"  [GmailTool] Sending email to {to}: {subject}")
    return {"status": "sent", "message_id": f"msg_{int(time.time())}"}


# ── OpenAI function definitions ───────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email via Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    }
]


# ── Main agent loop ───────────────────────────────────────────────────────────

async def run_agent(user_message: str):
    async with client:
        # Get a fresh AgentID token
        agent_token = await client.get_token()
        print(f"Agent token: {agent_token[:50]}...")

        try:
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI()
            messages = [{"role": "user", "content": user_message}]

            print(f"\nUser: {user_message}")

            # Initial call
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            message = response.choices[0].message

            # Handle tool calls
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    start = time.perf_counter()

                    print(f"\nAgent calling tool: {fn_name}({fn_args})")

                    # Execute with AgentID verification
                    if fn_name == "send_email":
                        result = await fake_gmail_send(
                            to=fn_args["to"],
                            subject=fn_args["subject"],
                            body=fn_args["body"],
                            agent_token=agent_token,
                        )
                    else:
                        result = {"error": f"Unknown tool: {fn_name}"}

                    duration_ms = int((time.perf_counter() - start) * 1000)
                    log_result = "allowed" if result.get("status") == "sent" else "denied"

                    # Log to AgentID audit trail
                    await client.log_action(
                        action=f"tool:{fn_name}",
                        resource=fn_args.get("to", "unknown"),
                        result=log_result,
                        prompt_snippet=user_message[:512],
                        tool_called=fn_name,
                        result_summary=str(result)[:256],
                        duration_ms=duration_ms,
                    )

                    print(f"  Result: {result}")
                    print(f"  Logged to AgentID audit trail")

        except ImportError:
            print("openai not installed — demonstrating AgentID flows only")

            # Demo without OpenAI: direct tool call with AgentID verification
            agent_token = await client.get_token()
            result = await fake_gmail_send(
                to="user@example.com",
                subject="Hello from AgentID",
                body="This email was sent by a verified AI agent.",
                agent_token=agent_token,
            )
            print(f"Tool result: {result}")

            await client.log_action(
                action="tool:send_email",
                resource="email:user@example.com",
                result="allowed" if result.get("status") == "sent" else "denied",
                tool_called="send_email",
                result_summary=str(result),
            )
            print("Action logged")


if __name__ == "__main__":
    asyncio.run(run_agent("Send a welcome email to pedro@example.com"))
