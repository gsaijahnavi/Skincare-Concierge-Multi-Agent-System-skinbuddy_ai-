# orchestrator_agent.py
"""
OrchestratorAgent: Coordinates all sub-agents and tools for the skincare concierge system.
"""
from typing import Any, Dict

class OrchestratorAgent:
    def __init__(self, intake_agent, routine_agent, compatibility_agent, evidence_rag_agent, calendar_agent):
        self.intake_agent = intake_agent
        self.routine_agent = routine_agent
        self.compatibility_agent = compatibility_agent
        self.evidence_rag_agent = evidence_rag_agent
        self.calendar_agent = calendar_agent

    def handle(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        # Intake user profile
        profile = self.intake_agent.intake(user_input)
        # Propose routine
        routine = self.routine_agent.propose_routine(profile)
        # Check compatibility
        compatibility = self.compatibility_agent.check_compatibility(profile, user_input.get("products", []))
        # Get evidence summary
        evidence = self.evidence_rag_agent.run(user_input.get("question", ""))
        # Get calendar events
        calendar_events = self.calendar_agent.get_events(profile.get("name", "user"))
        return {
            "profile": profile,
            "routine": routine,
            "compatibility": compatibility,
            "evidence": evidence,
            "calendar": calendar_events
        }
