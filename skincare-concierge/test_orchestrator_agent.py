import asyncio
import json

from agents.orchestrator_agent import OrchestratorAgent

# tools
from tools.profile_tool import ProfileDBTool
from tools.evidence_search_tool import EvidenceSearchTool
from tools.product_lookup_tool import ProductLookupTool
from tools.calendar_tool import CalendarTool
from tools.reminder_store import ReminderStore

# agents
from agents.intake_agent import IntakeAgent
from agents.safety_agent import SafetyAgent
from agents.evidence_rag_agent import EvidenceRAGAgent
from agents.product_lookup_agent import ProductLookupAgent
from agents.routine_agent import RoutineAgent
from agents.calendar_agent import CalendarAgent


async def simulate(orch, user_id, msg):
    print(f"\n🧑 USER: {msg}")
    response = await orch.run(user_id, msg)
    print("🤖 BOT:", json.dumps(response, indent=2))
    return response


async def main():

    # ===============================
    # Initialize full agent system
    # ===============================
    profile_tool = ProfileDBTool()
    evidence_tool = EvidenceSearchTool("data/evidence.xlsx")
    product_tool = ProductLookupTool()
    calendar_tool = CalendarTool()
    reminder_store = ReminderStore()

    intake = IntakeAgent(profile_tool)
    safety = SafetyAgent()
    evidence = EvidenceRAGAgent(tool=evidence_tool)
    product = ProductLookupAgent(product_tool)
    routine = RoutineAgent(product_tool)
    calendar = CalendarAgent(reminder_store, calendar_tool)

    orch = OrchestratorAgent(
        intake, safety, evidence, product, routine, calendar
    )

    user_id = "test_user"

    # ===============================
    # FULL MEMORY TEST
    # ===============================

    # 1. Create profile
    await simulate(orch, user_id, "Create my profile")

    # 2. Product recommendation
    await simulate(orch, user_id, "Suggest a moisturizer for dry acne prone skin")

    # 3. Follow-up using memory
    await simulate(orch, user_id, "Which one was cheapest among those products?")

    # 4. Evidence search
    await simulate(orch, user_id, "What evidence supports niacinamide?")

    # 5. Follow-up evidence
    await simulate(orch, user_id, "Does that evidence support treating acne?")

    # 6. Routine creation
    await simulate(orch, user_id, "Create a PM routine for me")

    # 7. Follow-up routine
    await simulate(orch, user_id, "Modify that routine by adding niacinamide")

    # 8. Set reminder for that routine
    step1 = await simulate(orch, user_id, "Remind me to follow that routine at 9 PM")

    # 9. Handle confirmation
    if step1.get("intent") == "calendar_plan":
        await simulate(orch, user_id, "yes")

    # 10. Check reminders
    await simulate(orch, user_id, "List my reminders")

    # 11. Delete reminder
    delete_step = await simulate(orch, user_id, "Delete my PM routine reminder")

    # 12. Confirm delete
    if delete_step.get("intent") == "calendar_plan":
        await simulate(orch, user_id, "yes")

    print("\n🎉 FULL MEMORY TEST COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
