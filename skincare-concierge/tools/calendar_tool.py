# calendar_tool.py

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarTool:
    def __init__(
        self,
        credentials_file: str = "/Users/gsaijahnavi/Downloads/Skincare-Concierge-Multi-Agent-System-skinbuddy_ai-/skincare-concierge/config/google/client_secret.json",  # rename your file to this or adjust path
        token_file: str = "token.json",
        calendar_id: str = "primary",
        timezone: str = "America/New_York",
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.calendar_id = calendar_id
        self.timezone = timezone
        self._service = None

    # ---------- AUTH / SERVICE ----------

    def _get_service(self):
        if self._service is not None:
            return self._service

        creds: Optional[Credentials] = None

        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    # ---------- EVENT OPS ----------

    def create_event(
        self,
        title: str,
        description: str,
        start_dt: datetime,
        recurrence: Optional[str] = None,
        duration_minutes: int = 15,
    ) -> str:
        service = self._get_service()
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        body = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": self.timezone,
            },
        }

        if recurrence and recurrence != "NONE":
            body["recurrence"] = [f"RRULE:FREQ={recurrence}"]

        event = service.events().insert(calendarId=self.calendar_id, body=body).execute()
        return event["id"]

    def delete_event(self, event_id: str) -> None:
        if not event_id:
            return
        service = self._get_service()
        service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
