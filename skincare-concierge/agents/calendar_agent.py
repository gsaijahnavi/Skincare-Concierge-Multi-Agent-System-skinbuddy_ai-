# calendar_agent.py

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from dateutil import parser as date_parser
from google import genai

from  tools.calendar_tool import CalendarTool
from tools.reminder_store import ReminderStore


MODEL_NAME = "models/gemini-2.5-flash-lite"


@dataclass
class CalendarPlan:
    question: str
    intent: str                 # "create" | "delete" | "list" | "update"
    needs_confirmation: bool
    payload: Dict[str, Any]


class CalendarAgent:
    def __init__(
        self,
        reminder_store: Optional[ReminderStore] = None,
        calendar_tool: Optional[CalendarTool] = None,
        model_name: str = MODEL_NAME,
    ):
        self.client = genai.Client()
        self.model_name = model_name
        self.store = reminder_store or ReminderStore()
        self.calendar = calendar_tool or CalendarTool()

    # ---------- LLM HELPER ----------

    def _llm(self, prompt: str) -> str:
        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        # New SDK usually exposes .text
        if hasattr(resp, "text") and resp.text:
            return resp.text
        # Fallback: join parts
        try:
            parts = []
            for cand in resp.candidates or []:
                for part in cand.content.parts or []:
                    if getattr(part, "text", None):
                        parts.append(part.text)
            return "\n".join(parts)
        except Exception:
            return ""

    # ---------- INTENT CLASSIFICATION ----------

    def _classify_intent(self, question: str) -> Dict[str, Any]:
        prompt = f"""
You are a reminder intent classifier for a skincare+wellness assistant.

User question:
\"\"\"{question}\"\"\"


Decide the intent and extract basic fields.

Respond with STRICT JSON ONLY in this format:
{{
  "intent": "create" | "delete" | "list" | "update",
  "title_hint": "<short title for the reminder if applicable, e.g. 'AM Skincare Routine'>",
  "datetime_text": "<time phrase from the question or empty string>",
  "recurrence": "NONE" | "DAILY" | "WEEKLY" | "MONTHLY",
  "all_reminders": true | false
}}
"""
        raw = self._llm(prompt)
        try:
            data = json.loads(raw)
        except Exception:
            # Try to salvage JSON
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(raw[start : end + 1])
            else:
                data = {}

        # Minimal defaults
        return {
            "intent": data.get("intent", "create"),
            "title_hint": data.get("title_hint") or "",
            "datetime_text": data.get("datetime_text") or "",
            "recurrence": data.get("recurrence", "DAILY"),
            "all_reminders": bool(data.get("all_reminders", False)),
        }

    # ---------- TITLE-BASED MATCHING (your requirement) ----------

    def _match_titles(self, question: str, titles: List[str]) -> Dict[str, Any]:
        """
        Use LLM to match reminders based ONLY on title.
        Returns titles in `matches`.
        """
        reminders_titles = titles

        prompt = f"""
You are a reminder-matching engine.

Your task is to decide which existing reminders match the user's deletion or update request.

IMPORTANT RULES:
- Match reminders ONLY based on the similarity of the reminder TITLE.
- Ignore date, time, recurrence, and description.
- Use semantic reasoning (e.g., "AM routine" ≈ "Morning Skincare Routine").
- If the user says "all reminders", then match ALL.
- Return STRICT JSON ONLY, no extra text.

USER REQUEST:
"{question}"

EXISTING REMINDERS (titles only):
{json.dumps(reminders_titles, indent=2)}

Respond EXACTLY in this JSON format:
{{
  "matches": ["title1", "title2"],
  "confidence": "high" | "medium" | "low",
  "explanation": "<short explanation of why these titles match>"
}}
        """

        raw = self._llm(prompt)
        try:
            data = json.loads(raw)
        except Exception:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(raw[start : end + 1])
            else:
                data = {}

        matches = data.get("matches", []) or []
        # Ensure they are strings and also present in titles
        matches = [m for m in matches if isinstance(m, str) and m in titles]

        return {
            "matches": matches,
            "confidence": data.get("confidence", "low"),
            "explanation": data.get("explanation", ""),
        }

    # ---------- TIME PARSING HELP ----------

    def _resolve_datetime(self, datetime_text: str) -> datetime:
        """
        Very simple helper: parse time from text. If only time is present,
        assume 'next occurrence' today or tomorrow.
        """
        if not datetime_text:
            # default: next 10 minutes
            return datetime.now() + timedelta(minutes=10)

        try:
            dt = date_parser.parse(datetime_text, fuzzy=True)
            # If no date part: assume today or tomorrow
            if dt.date() == datetime(1900, 1, 1).date():
                today = datetime.now()
                dt = dt.replace(year=today.year, month=today.month, day=today.day)
                if dt < today:
                    dt = dt + timedelta(days=1)
            return dt
        except Exception:
            return datetime.now() + timedelta(minutes=10)

    # ---------- PLAN ----------

    def plan(self, question: str, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Returns a plan dict (JSON-serializable).
        Does NOT modify calendar or reminders yet.
        """

        intent_info = self._classify_intent(question)
        intent = intent_info["intent"]

        if intent == "list":
            # listing is safe, no confirmation needed
            return {
                "question": question,
                "intent": "list",
                "needs_confirmation": False,
                "payload": {},
            }

        if intent == "delete":
            existing = self.store.list_reminders()
            titles = [r.get("title", "") for r in existing if r.get("title")]

            if not titles:
                return {
                    "question": question,
                    "intent": "delete",
                    "needs_confirmation": False,
                    "payload": {
                        "matches": [],
                        "explanation": "No reminders stored.",
                    },
                }

            match_result = self._match_titles(question, titles)

            return {
                "question": question,
                "intent": "delete",
                "needs_confirmation": bool(match_result["matches"]),  # ask before deleting
                "payload": {
                    "matches": match_result["matches"],  # TITLES ONLY ✅
                    "confidence": match_result["confidence"],
                    "explanation": match_result["explanation"],
                },
            }

        # Default / CREATE
        title_hint = intent_info["title_hint"] or "Skincare Reminder"
        dt = self._resolve_datetime(intent_info["datetime_text"])
        recurrence = intent_info["recurrence"]
        profile_str = json.dumps(user_profile or {}, ensure_ascii=False)

        description = f"{question} | Profile: {profile_str}"

        return {
            "question": question,
            "intent": "create",
            "needs_confirmation": True,
            "payload": {
                "title": title_hint,
                "description": description,
                "datetime_iso": dt.isoformat(),
                "recurrence": recurrence,
            },
        }

    # ---------- EXECUTE ----------

    def execute(
        self,
        plan: Dict[str, Any],
        confirm: bool = True,
        selected_titles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the plan. For delete with multiple matches:
        - `selected_titles` can be used by caller (CLI) to pass which titles to delete.
        """

        intent = plan.get("intent")
        question = plan.get("question", "")

        if not confirm and intent in ("create", "delete", "update"):
            return {
                "question": question,
                "intent": intent,
                "status": "cancelled",
                "details": "User did not confirm.",
            }

        if intent == "list":
            reminders = self.store.list_reminders()
            return {
                "question": question,
                "intent": "list",
                "status": "ok",
                "reminders": reminders,
            }

        if intent == "create":
            payload = plan.get("payload", {})
            title = payload.get("title", "Skincare Reminder")
            description = payload.get("description", question)
            dt_iso = payload.get("datetime_iso")
            recurrence = payload.get("recurrence", "DAILY")

            dt = datetime.fromisoformat(dt_iso) if dt_iso else datetime.now().isoformat()

            event_id = self.calendar.create_event(
                title=title,
                description=description,
                start_dt=dt,
                recurrence=recurrence,
            )

            reminder = self.store.add_reminder(
                {
                    "title": title,
                    "description": description,
                    "datetime": dt.isoformat(),
                    "recurrence": recurrence,
                    "google_event_id": event_id,
                    "source_agent": "calendar_agent",
                }
            )

            return {
                "question": question,
                "intent": "create",
                "status": "created",
                "reminder": reminder,
            }

        if intent == "delete":
            payload = plan.get("payload", {})
            matches = payload.get("matches", [])

            if selected_titles is not None and selected_titles:
                titles_to_delete = selected_titles
            else:
                titles_to_delete = matches

            if not titles_to_delete:
                return {
                    "question": question,
                    "intent": "delete",
                    "status": "no_matches",
                    "deleted": [],
                }

            # Map titles → reminders → delete from calendar + store
            to_delete_reminders = self.store.find_by_titles(titles_to_delete)
            deleted_titles = []

            for r in to_delete_reminders:
                event_id = r.get("google_event_id")
                if event_id:
                    try:
                        self.calendar.delete_event(event_id)
                    except Exception:
                        # Ignore failures but keep going
                        pass
                deleted_titles.append(r.get("title"))

            # Remove from store
            self.store.delete_by_titles(deleted_titles)

            return {
                "question": question,
                "intent": "delete",
                "status": "deleted",
                "deleted_titles": deleted_titles,
            }

        # UPDATE can be implemented later
        return {
            "question": question,
            "intent": intent,
            "status": "not_implemented",
        }
