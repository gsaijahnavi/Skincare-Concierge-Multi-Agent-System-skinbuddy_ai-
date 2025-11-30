# tools/calendar_storage.py

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


REMINDER_FILE = os.path.join(os.path.dirname(__file__), "../data/reminders.json")


class CalendarStorage:
    """
    Local JSON storage for reminders.

    Each reminder entry:
    {
      "id": "<internal UUID>",
      "title": "Drink water",
      "summary": "Daily hydration reminder",
      "start_datetime": "2025-12-01T19:00:00",
      "recurrence": "DAILY" | "WEEKLY" | None,
      "google_event_id": "<GCal event id>",
      "created_at": "...",
      "updated_at": "..."
    }
    """

    def __init__(self, path: str = REMINDER_FILE):
        self.path = os.path.abspath(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ---------- core load/save ----------

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
            except json.JSONDecodeError:
                return []

    def _save(self, reminders: List[Dict[str, Any]]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2, ensure_ascii=False)

    # ---------- CRUD helpers ----------

    def list_reminders(self) -> List[Dict[str, Any]]:
        return self._load()

    def add_reminder(
        self,
        title: str,
        summary: str,
        start_datetime_iso: str,
        recurrence: Optional[str],
        google_event_id: str,
    ) -> Dict[str, Any]:
        reminders = self._load()
        now = datetime.utcnow().isoformat()

        reminder = {
            "id": str(uuid.uuid4()),
            "title": title,
            "summary": summary,
            "start_datetime": start_datetime_iso,
            "recurrence": recurrence,
            "google_event_id": google_event_id,
            "created_at": now,
            "updated_at": now,
        }

        reminders.append(reminder)
        self._save(reminders)
        return reminder

    def update_reminder(
        self,
        reminder_id: Optional[str] = None,
        title_contains: Optional[str] = None,
        updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update by id OR fuzzy match on title substring.
        """
        if updates is None:
            updates = {}

        reminders = self._load()
        target = None

        for r in reminders:
            if reminder_id and r["id"] == reminder_id:
                target = r
                break
            if title_contains and title_contains.lower() in r["title"].lower():
                target = r
                break

        if not target:
            return None

        for k, v in updates.items():
            target[k] = v
        target["updated_at"] = datetime.utcnow().isoformat()

        self._save(reminders)
        return target

    def delete_reminder(
        self,
        reminder_id: Optional[str] = None,
        title_contains: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        reminders = self._load()
        target = None
        new_list = []

        for r in reminders:
            matched = False
            if reminder_id and r["id"] == reminder_id:
                matched = True
            elif title_contains and title_contains.lower() in r["title"].lower():
                matched = True

            if matched and target is None:
                target = r
                continue

            new_list.append(r)

        if target:
            self._save(new_list)

        return target

    def find_by_title(self, title_contains: str) -> List[Dict[str, Any]]:
        reminders = self._load()
        return [
            r for r in reminders
            if title_contains.lower() in r["title"].lower()
        ]
