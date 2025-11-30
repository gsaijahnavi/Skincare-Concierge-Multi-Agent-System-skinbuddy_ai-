import asyncio
from agents.evidence_rag_agent import EvidenceRAGAgent
from tools.evidence_search_tool import EvidenceSearchTool
from google.adk.runners import InMemoryRunner
from google.genai import types


async def main():

    tool = EvidenceSearchTool("data/evidence.xlsx")
    agent = EvidenceRAGAgent(tool=tool)

    runner = InMemoryRunner(agent=agent, app_name="agents")

    # Create session
    session = await runner.session_service.create_session(
        app_name="agents",
        user_id="test_user"
    )

    # Message
    new_message = types.Content(
        role="user",
        parts=[types.Part(text="what ingredients suite acne-prone dry skin?")]
    )

    # ⭐ FIX: use async version (no background threads)
    async for ev in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=new_message
    ):

        if hasattr(ev, "content") and ev.content:
            if ev.content.role in ("assistant", "model"):
                parts = ev.content.parts
                if parts:
                    print("\nFINAL AGENT OUTPUT:\n")
                    print(parts[0].text)


if __name__ == "__main__":
    asyncio.run(main())
