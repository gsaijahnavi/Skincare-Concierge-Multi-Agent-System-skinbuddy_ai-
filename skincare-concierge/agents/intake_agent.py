import re
from typing import Dict, Any

class IntakeAgent:
    def __init__(self, profile_tool):
        self.profile_tool = profile_tool
        self.profile_questions = [
            "Name?",
            "Age?",
            "Skin type (e.g., oily, dry, combination)",
            "Skin concerns (e.g., acne, sensitivity)",
            "Current Skincare routine",
            "Budget preference"
        ]

    def classify_intent(self, query: str) -> str:
        query = query.lower()
        # Add more robust matching for update intent
        if any(k in query for k in ["create", "new profile", "sign up"]):
            return "create"
        elif any(k in query for k in ["fetch", "show", "view", "display"]):
            return "fetch"
        elif any(k in query for k in ["update", "edit", "change", "update profile"]):
            return "update"
        elif "profile" in query:
            # If only 'profile' is present, default to fetch
            return "fetch"
        return "unknown"

    async def handle(self, user_id: str, query: str, ask_fn=None) -> str:
        intent = self.classify_intent(query)
        profile = await self.profile_tool.get_profile(user_id)

        if intent == "create":
            if profile:
                return f"Profile already exists for user {user_id}."
            answers = {}
            for q in self.profile_questions:
                if ask_fn:
                    ans = await ask_fn(q)
                else:
                    ans = input(q + " ")
                answers[q] = ans
            await self.profile_tool.save_profile(user_id, answers)
            return f"Profile created for user {user_id}."

        elif intent == "fetch":
            if not profile:
                return f"No profile found for user {user_id}."
            return f"Profile for {user_id}:\n" + "\n".join(f"{k}: {v}" for k, v in profile.items())

        elif intent == "update":
            if not profile:
                return f"No profile found for user {user_id}."
            for q in self.profile_questions:
                if ask_fn:
                    ans = await ask_fn(f"Update {q} (current: {profile.get(q, 'N/A')}) or press Enter to keep:")
                else:
                    ans = input(f"Update {q} (current: {profile.get(q, 'N/A')}) or press Enter to keep: ")
                if ans:
                    profile[q] = ans
            await self.profile_tool.update_profile(user_id, profile)
            return f"Profile updated for user {user_id}."

        else:
            return "Sorry, I couldn't understand your request. Please specify if you want to create, fetch, or update your profile."
