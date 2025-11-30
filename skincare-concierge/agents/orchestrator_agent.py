# orchestrator_agent.py

import asyncio
from typing import Any, Dict, Optional

from agents.intake_agent import IntakeAgent
from agents.safety_agent import SafetyAgent
from agents.evidence_rag_agent import EvidenceRAGAgent
from agents.product_lookup_agent import ProductLookupAgent
from agents.routine_agent import RoutineAgent
from agents.calendar_agent import CalendarAgent


class OrchestratorAgent:
    """
    FULL MEMORY VERSION
    - remembers entire conversation
    - remembers last products, routines, evidence
    - handles follow-up questions
    - supports multi-turn workflows
    - supports calendar confirmations
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

        # ------------------------------
        # FULL CONVERSATION MEMORY
        # ------------------------------
        self.conversation_history: Dict[str, list] = {}

        # ------------------------------
        # LONG TERM USER STATE MEMORY
        # ------------------------------
        self.user_state: Dict[str, Dict[str, Any]] = {}

    # ============================================================
    # MEMORY HELPERS
    # ============================================================

    def _init_user_state(self, user_id):
        if user_id not in self.user_state:
            self.user_state[user_id] = {
                "profile": {},
                "last_routine": None,
                "last_products": None,
                "last_evidence": None,
                "pending_calendar_plan": None,
            }
            self.conversation_history[user_id] = []

    def _remember(self, user_id, user_msg, assistant_msg):
        """Store conversation turns."""
        self.conversation_history[user_id].append({
            "user": user_msg,
            "assistant": assistant_msg
        })

    def _save_state(self, user_id, key, value):
        self.user_state[user_id][key] = value

    # ============================================================
    # INTENT CLASSIFICATION
    # ============================================================

    def classify_intent(self, text: str) -> str:
        t = text.lower()

        # YES/NO: for confirmation
        if t in ["yes", "no", "y", "n"]:
            return "confirmation"

        # Calendar
        if any(k in t for k in ["remind", "at ", "schedule", "alarm"]):
            return "calendar"

        # Profile
        if "profile" in t:
            return "profile"

        # Follow-up references
        if "those products" in t or "them" in t:
            return "followup_products"

        if "that routine" in t:
            return "followup_routine"

        if "that evidence" in t:
            return "followup_evidence"

        # Ingredient → evidence
        ING = [
            "niacinamide", "retinol", "tretinoin", "vitamin c", "salicylic",
            "bha", "aha", "glycolic", "lactic", "arbutin", "kojic",
            "tranexamic", "ceramide"
        ]
        if any(i in t for i in ING):
            return "evidence"

        # Product request
        if any(k in t for k in ["suggest", "recommend"]):
            return "product"

        # Routine
        if "routine" in t:
            return "routine"

        return "none"

    # ============================================================
    # MAIN RUN LOOP
    # ============================================================

    async def run(self, user_id: str, query: str):

        # Initialize memory
        self._init_user_state(user_id)

        # Safety first
        safe = self.safety_agent.intercept(query)
        if safe != "safe":
            return {"intent": "unsafe", "message": safe}

        intent = self.classify_intent(query)

        # ---------------------------------------------------------
        # Handle confirmation ("yes/no")
        # ---------------------------------------------------------
        if intent == "confirmation":
            pending = self.user_state[user_id]["pending_calendar_plan"]

            if not pending:
                return {"intent": "none", "message": "There is nothing to confirm."}

            if query.lower() in ["yes", "y"]:
                result = self.calendar_agent.execute(pending, confirm=True)
                self.user_state[user_id]["pending_calendar_plan"] = None
                return {"intent": "calendar", "result": result, "message": "Reminder set!"}

            if query.lower() in ["no", "n"]:
                self.user_state[user_id]["pending_calendar_plan"] = None
                return {"intent": "calendar", "message": "Okay, I cancelled the reminder."}

        # ---------------------------------------------------------
        # PROFILE
        # ---------------------------------------------------------
        if intent == "profile":
            result = await self.intake_agent.handle(user_id, query)
            self._save_state(user_id, "profile", await self.intake_agent.profile_tool.get_profile(user_id))
            return {"intent": "profile", "result": result}

        # ---------------------------------------------------------
        # EVIDENCE
        # ---------------------------------------------------------
        if intent == "evidence":
            ev = self.evidence_agent.run(query)
            self._save_state(user_id, "last_evidence", ev)
            return {"intent": "evidence", "evidence": ev}

        # ---------------------------------------------------------
        # PRODUCT
        # ---------------------------------------------------------
        if intent == "product":
            profile = self.user_state[user_id]["profile"]
            prod = self.product_agent.run(query, user_profile=profile)
            self._save_state(user_id, "last_products", prod)
            return {"intent": "product", "products": prod}

        # ---------------------------------------------------------
        # ROUTINE
        # ---------------------------------------------------------
        if intent == "routine":
            profile = self.user_state[user_id]["profile"]
            routine = self.routine_agent.run(query, profile)
            self._save_state(user_id, "last_routine", routine)
            return {"intent": "routine", "routine": routine}

        # ---------------------------------------------------------
        # FOLLOW-UP PRODUCTS
        # ---------------------------------------------------------
        if intent == "followup_products":
            last_prod = self.user_state[user_id]["last_products"]
            if not last_prod:
                return {"message": "I don’t have previous products to reference."}
            return {"intent": "followup_products", "products": last_prod}

        # ---------------------------------------------------------
        # CALENDAR
        # ---------------------------------------------------------
        if intent == "calendar":
            profile = self.user_state[user_id]["profile"]
            plan = self.calendar_agent.plan(query, profile)

            if plan.get("needs_confirmation"):
                self.user_state[user_id]["pending_calendar_plan"] = plan
                return {
                    "intent": "calendar_plan",
                    "message": "Do you want me to set this reminder? (yes/no)",
                    "plan": plan
                }

            executed = self.calendar_agent.execute(plan, confirm=True)
            return {"intent": "calendar", "result": executed}

        # ---------------------------------------------------------
        # DEFAULT
        # ---------------------------------------------------------
        return {"intent": "none", "message": "How can I help with skincare today?"}
