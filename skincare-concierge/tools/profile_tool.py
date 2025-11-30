import json
import os
from google.adk.tools import AgentTool, ToolContext

PROFILE_PATH = "data/user_profiles.json"


class ProfileDBTool(AgentTool):
    name = "profile_db_tool"
    description = "Reads and writes user skincare profiles."

    def __init__(self, agent=None):
        # Pass a default agent if none is provided
        if agent is None:
            from google.adk.agents import LlmAgent
            from google.adk.models.google_llm import Gemini
            agent = LlmAgent(name="profile_db_agent", model=Gemini(model="gemini-2.5-flash-lite"), description="Profile DB agent")
        super().__init__(agent=agent)

        # Ensure directory + file exist
        os.makedirs("data", exist_ok=True)

        if not os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "w") as f:
                json.dump({}, f)

    def _load_all(self):
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)

    def _save_all(self, data):
        with open(PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def run(self, context: ToolContext, *, action, user_id, payload=None):
        data = self._load_all()

        # FETCH
        if action == "fetch":
            return data.get(user_id, {})

        # CREATE
        if action == "create":
            data[user_id] = payload
            self._save_all(data)
            return {"status": "created", "profile": payload}

        # UPDATE
        if action == "update":
            existing = data.get(user_id, {})
            existing.update(payload)
            data[user_id] = existing
            self._save_all(data)
            return {"status": "updated", "profile": existing}

        return {"error": "unknown action"}

    # Add async get_profile, save_profile, update_profile for compatibility
    async def get_profile(self, user_id):
        # Simulate async for compatibility
        return self._load_all().get(user_id, {})

    async def save_profile(self, user_id, profile):
        data = self._load_all()
        data[user_id] = profile
        self._save_all(data)

    async def update_profile(self, user_id, profile):
        data = self._load_all()
        existing = data.get(user_id, {})
        existing.update(profile)
        data[user_id] = existing
        self._save_all(data)
