"""macOS native read-only adapters."""

from __future__ import annotations

import json
import platform
import plistlib
import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentfeeds_runtime.adapters.common import envelope, stable_hash
from agentfeeds_runtime.adapters.local_sources import fetch_local_directory


def _require_macos(stream: dict) -> None:
    if platform.system() != "Darwin":
        raise RuntimeError(f"{stream['id']}: this template requires macOS")


def _osascript(stream: dict, script: str) -> str:
    _require_macos(stream)
    result = subprocess.run(["osascript", "-e", script], check=False, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"{stream['id']}: osascript failed: {result.stderr.strip()}")
    return result.stdout


def _rows(output: str, min_parts: int) -> list[list[str]]:
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= min_parts:
            rows.append(parts)
    return rows


def fetch_mac_calendar(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    scope = adapter.get("scope") or "today"
    days = int(adapter.get("days") or (7 if scope == "upcoming" else 1))
    start_offset = 0
    script = f'''
set startDate to current date
set hours of startDate to 0
set minutes of startDate to 0
set seconds of startDate to 0
set startDate to startDate + ({start_offset} * days)
set endDate to startDate + ({days} * days)
set rows to {{}}
tell application "Calendar"
  repeat with cal in calendars
    set calName to name of cal
    set matches to every event of cal whose start date is greater than or equal to startDate and start date is less than endDate
    repeat with ev in matches
      set evLocation to ""
      try
        set evLocation to location of ev
      end try
      set end of rows to (uid of ev) & tab & (summary of ev) & tab & ((start date of ev) as string) & tab & ((end date of ev) as string) & tab & evLocation & tab & calName
    end repeat
  end repeat
end tell
set AppleScript's text item delimiters to linefeed
return rows as text
'''
    events = []
    for uid, summary, starts_at, ends_at, location, *_rest in _rows(_osascript(stream, script), 5):
        data = {"uid": uid, "summary": summary or "(untitled event)", "starts_at": starts_at, "ends_at": ends_at, "location": location or None}
        events.append(envelope(stream, stream_uri, uid or stable_hash(data), data, starts_at or None))
    return events


def fetch_mac_reminders(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    include_completed = "true" if adapter.get("include_completed") else "false"
    script = f'''
set rows to {{}}
tell application "Reminders"
  repeat with listRef in lists
    set listName to name of listRef
    set matches to every reminder of listRef whose completed is {include_completed}
    repeat with remRef in matches
      set bodyText to ""
      set dueText to ""
      set priorityValue to 0
      try
        set bodyText to body of remRef
      end try
      try
        set dueText to (due date of remRef) as string
      end try
      try
        set priorityValue to priority of remRef
      end try
      set end of rows to (id of remRef) & tab & (name of remRef) & tab & ((completed of remRef) as string) & tab & listName & tab & dueText & tab & (priorityValue as string) & tab & bodyText
    end repeat
  end repeat
end tell
set AppleScript's text item delimiters to linefeed
return rows as text
'''
    events = []
    for reminder_id, title, completed, list_name, due_at, priority, notes, *_rest in _rows(_osascript(stream, script), 7):
        data = {
            "id": reminder_id,
            "title": title or "(untitled reminder)",
            "completed": completed.lower() == "true",
            "list_name": list_name,
            "due_at": due_at or None,
            "priority": int(priority) if priority.isdigit() else None,
            "notes_snippet": (notes or None),
            "updated_at": due_at or None,
            "url": None,
        }
        events.append(envelope(stream, stream_uri, reminder_id or stable_hash(data), data, due_at or None))
    return events


def fetch_mac_mail(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    limit = int(adapter.get("limit") or 50)
    script = f'''
set rows to {{}}
tell application "Mail"
  set matches to messages of inbox whose read status is false
  set maxItems to count of matches
  if maxItems > {limit} then set maxItems to {limit}
  repeat with i from 1 to maxItems
    set msg to item i of matches
    set previewText to ""
    try
      set previewText to content of msg
      if length of previewText > 300 then set previewText to text 1 thru 300 of previewText
    end try
    set end of rows to (message id of msg) & tab & (subject of msg) & tab & (sender of msg) & tab & ((date received of msg) as string) & tab & previewText
  end repeat
end tell
set AppleScript's text item delimiters to linefeed
return rows as text
'''
    events = []
    for message_id, subject, sender, received_at, snippet, *_rest in _rows(_osascript(stream, script), 5):
        data = {
            "id": message_id,
            "subject": subject or "(no subject)",
            "sender": sender,
            "from_email": None,
            "received_at": received_at,
            "unread": True,
            "mailbox": "Inbox",
            "account": None,
            "snippet": snippet or None,
        }
        events.append(envelope(stream, stream_uri, message_id or stable_hash(data), data, received_at or None))
    return events


def fetch_mac_notes(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    limit = int(adapter.get("limit") or 20)
    script = f'''
set rows to {{}}
tell application "Notes"
  set allNotes to notes
  set maxItems to count of allNotes
  if maxItems > {limit} then set maxItems to {limit}
  repeat with i from 1 to maxItems
    set n to item i of allNotes
    set bodyText to plaintext of n
    if length of bodyText > 300 then set bodyText to text 1 thru 300 of bodyText
    set folderName to ""
    try
      set folderName to name of container of n
    end try
    set end of rows to (id of n) & tab & (name of n) & tab & bodyText & tab & ((modification date of n) as string) & tab & folderName
  end repeat
end tell
set AppleScript's text item delimiters to linefeed
return rows as text
'''
    events = []
    for note_id, title, snippet, modified_at, folder, *_rest in _rows(_osascript(stream, script), 5):
        data = {"id": note_id, "title": title or "(untitled note)", "snippet": snippet or "", "modified_at": modified_at, "folder": folder or None, "account": None}
        events.append(envelope(stream, stream_uri, note_id or stable_hash(data), data, modified_at or None))
    return events


def _mac_absolute_epoch(value: float) -> str:
    dt = datetime(2001, 1, 1, tzinfo=UTC) + timedelta(seconds=float(value))
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _walk_reading_list(node: object) -> list[dict]:
    items = []
    if isinstance(node, dict):
        uri = node.get("URLString")
        extra = node.get("ReadingList") or {}
        if uri and extra:
            items.append(
                {
                    "title": node.get("URIDictionary", {}).get("title") or uri,
                    "url": uri,
                    "added_at": _mac_absolute_epoch(extra["DateAdded"]) if extra.get("DateAdded") else None,
                    "preview_text": extra.get("PreviewText"),
                }
            )
        for value in node.values():
            items.extend(_walk_reading_list(value))
    elif isinstance(node, list):
        for value in node:
            items.extend(_walk_reading_list(value))
    return items


def fetch_safari_reading_list(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    _require_macos(stream)
    path = Path(adapter["path"]).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"{stream['id']}: Safari bookmarks file not found: {path}")
    payload = plistlib.loads(path.read_bytes())
    items = _walk_reading_list(payload)
    items.sort(key=lambda item: item.get("added_at") or "", reverse=True)
    limit = int(adapter.get("limit") or 50)
    return [envelope(stream, stream_uri, item["url"], item, item.get("added_at")) for item in items[:limit]]


def fetch_imessage_sqlite(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    _require_macos(stream)
    path = Path(adapter["database"]).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"{stream['id']}: Messages database not found: {path}")
    limit = int(adapter.get("limit") or 25)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT chat.ROWID, chat.display_name, message.text, message.date
            FROM chat
            JOIN chat_message_join ON chat.ROWID = chat_message_join.chat_id
            JOIN message ON message.ROWID = chat_message_join.message_id
            WHERE message.is_read = 0
            ORDER BY message.date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    events = []
    for thread_id, display_name, snippet, raw_date in rows:
        last_message_at = _mac_absolute_epoch((raw_date or 0) / 1_000_000_000)
        data = {
            "thread_id": str(thread_id),
            "display_name": display_name or "Messages conversation",
            "participants": [],
            "unread_count": 1,
            "last_message_at": last_message_at,
            "snippet": snippet or "",
        }
        events.append(envelope(stream, stream_uri, thread_id, data, last_message_at))
    return events


def fetch_finder_recent_downloads(stream: dict, adapter: dict, stream_uri: str) -> list[dict]:
    _require_macos(stream)
    return fetch_local_directory(stream, adapter, stream_uri)
