# orchestrator_agent.py

import re
import asyncio
from typing import Any, Dict, Optional

# Import your agents
from agents.intake_agent import IntakeAgent
from agents.safety_agent import SafetyAgent
from agents.evidence_rag_agent import EvidenceRAGAgent
from agents.product_lookup_agent import ProductLookupAgent
from agents.routine_agent import RoutineAgent
from agents.calendar_agent import CalendarAgent


class OrchestratorAgent:
    """
    A central agent that routes user queries to the correct sub-agent.

    - Safety agent ALWAYS runs first.
    - Intent classification decides which agent(s) should run.
    - Supports parallel: Evidence + Product for mixed ingredient queries.
    - Supports sequential: Product → Routine.
    - Supports loops: Calendar plan → user confirmation → execute.
    """

    def __init__(
        self,
        intake_agent: IntakeAgent,
        safety_agent: SafetyAgent,
        evidence_agent: EvidenceRAGAgent,
        product_agent: ProductLookupAgent,
        routine_agent: RoutineAgent,
        calendar_agent: CalendarAgent,
    ):
        self.intake_agent = intake_agent
        self.safety_agent = safety_agent
        self.evidence_agent = evidence_agent
        self.product_agent = product_agent
        self.routine_agent = routine_agent
        self.calendar_agent = calendar_agent

    # -------------------------------------------------------------------
    # INTENT CLASSIFICATION
    # -------------------------------------------------------------------

    def classify_intent(self, text: str) -> str:
        t = text.lower()

        # Profile management
        if any(k in t for k in ["profile", "create profile", "update profile", "view my profile"]):
            return "profile"

        # Calendar / reminders
        if any(k in t for k in ["reminder", "schedule", "alarm", "notify", "calendar"]):
            return "calendar"

        # Ingredient signals (Evidence)
        ING = [
            "niacinamide", "retinol", "tretinoin", "vitamin c", "ascorbic",
            "azelaic", "salicylic", "bha", "aha", "glycolic", "lactic",
            "arbutin", "kojic", "tranexamic", "ceramide"
        ]
        ingredient_found = any(i in t for i in ING)

        # Product/recommendation keywords
        product_keywords = ["suggest", "recommend", "which product", "give me a product"]

        # Routine keywords
        routine_keywords = ["routine", "am routine", "pm routine", "night routine"]

        if ingredient_found and any(k in t for k in product_keywords + routine_keywords):
            return "mixed_condition"       # → parallel Evidence + Product

        if ingredient_found:
            return "evidence"

        if any(k in t for k in product_keywords):
            return "product"

        if any(k in t for k in routine_keywords):
            return "routine"

        return "none"

    # -------------------------------------------------------------------
    # MAIN ENTRYPOINT
    # -------------------------------------------------------------------

    async def run(self, user_id: str, query: str) -> Dict[str, Any]:

        # ---------------- SAFETY CHECK ----------------
        safety_result = self.safety_agent.intercept(query)
        if safety_result != "safe":
            return {"intent": "unsafe", "message": safety_result}

        # ---------------- INTENT ----------------------
        intent = self.classify_intent(query)

        # ---------------- PROFILE ---------------------
        if intent == "profile":
            return await self.intake_agent.handle(user_id, query)

        # ---------------- EVIDENCE --------------------
        if intent == "evidence":
            result = self.evidence_agent.run(query)
            return {"intent": "evidence", "evidence": result}

        # ---------------- PRODUCT ---------------------
        if intent == "product":
            profile = await self._safe_get_profile(user_id)
            result = self.product_agent.run(query, user_profile=profile)
            return {"intent": "product", "products": result}

        # ---------------- ROUTINE ---------------------
        if intent == "routine":
            profile = await self._safe_get_profile(user_id)
            result = self.routine_agent.run(query, profile)
            return {"intent": "routine", "routine": result}

        # ---------------- MIXED = Parallel ------------
        if intent == "mixed_condition":
            profile = await self._safe_get_profile(user_id)

            evidence_fut = asyncio.to_thread(self.evidence_agent.run, query)
            product_fut = asyncio.to_thread(self.product_agent.run, query, profile)

            evidence_result, product_result = await asyncio.gather(
                evidence_fut, product_fut
            )

            return {
                "intent": "mixed_condition",
                "evidence": evidence_result,
                "products": product_result,
            }

        # ---------------- CALENDAR ---------------------
        if intent == "calendar":
            profile = await self._safe_get_profile(user_id)

            # Step 1: Plan
            plan = self.calendar_agent.plan(query, profile)

            if plan.get("needs_confirmation"):
                # Orchestrator sends plan back, waiting for user confirm
                return {
                    "intent": "calendar_plan",
                    "plan": plan,
                    "message": "Confirm? (yes/no)"
                }

            # If no confirmation needed → execute immediately
            execute_result = self.calendar_agent.execute(plan, confirm=True)
            return {"intent": "calendar", "result": execute_result}

        # ---------------- NONE / default --------------
        return {"intent": "none", "message": "How can I help with skincare today?"}

    # -------------------------------------------------------------------
    # PROFILE LOADER SAFE
    # -------------------------------------------------------------------
    async def _safe_get_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            p = await self.intake_agent.profile_tool.get_profile(user_id)
            return p or {}
        except Exception:
            return {}
