# reminder_store.py

import json
import os
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4


class ReminderStore:
    def __init__(self, path: str = "data/reminders.json"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._data = {"reminders": []}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self._data = json.load(f)
                if "reminders" not in self._data:
                    self._data = {"reminders": []}
            except Exception:
                self._data = {"reminders": []}
        else:
            self._data = {"reminders": []}

    def _save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    # ---------- BASIC OPS ----------

    def list_reminders(self) -> List[Dict[str, Any]]:
        return list(self._data.get("reminders", []))

    def add_reminder(self, reminder: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in reminder:
            reminder["id"] = f"rem_{uuid4().hex[:8]}"
        reminder["created_at"] = datetime.utcnow().isoformat()
        self._data.setdefault("reminders", []).append(reminder)
        self._save()
        return reminder

    def delete_by_titles(self, titles: list[str]) -> List[Dict[str, Any]]:
        """Delete reminders whose title is in the given list of titles."""
        titles_set = set(titles)
        all_rems = self._data.get("reminders", [])
        kept = []
        deleted = []

        for r in all_rems:
            if r.get("title") in titles_set:
                deleted.append(r)
            else:
                kept.append(r)

        self._data["reminders"] = kept
        self._save()
        return deleted

    def find_by_titles(self, titles: list[str]) -> List[Dict[str, Any]]:
        titles_set = set(titles)
        return [r for r in self._data.get("reminders", []) if r.get("title") in titles_set]
