from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import date, datetime, time, timedelta
from src.scraper import Entry
from dataclasses import dataclass

import os

@dataclass
class Event:
    is_all_day: bool
    id: str | None
    title: str
    description: str
    start: datetime | date
    end: datetime | date | None = None
    
    def __post_init__(self) -> None:
        if self.is_all_day:
            if not isinstance(self.start, date) or isinstance(self.start, datetime):
                raise TypeError("All-day events must use date (not datetime) for start")
            if not self.end:
                self.end = self.start + timedelta(days=1)
            elif not isinstance(self.end, date) or isinstance(self.end, datetime):
                raise TypeError("All-day events must use date (not datetime) for end")
            
        else:
            if not isinstance(self.start, datetime):
                raise TypeError("Timed events must use datetime for start")
            if not isinstance(self.end, datetime):
                raise TypeError("Timed events must use datetime for end")
    
    def __repr__(self) -> str:
        day = self.start.date().isoformat() if isinstance(self.start, datetime) else self.start.isoformat()
        if isinstance(self.start, datetime) and isinstance(self.end, datetime):
            times = self.start.time().strftime('%-I:%M%p')
            times += ' - ' + self.end.time().strftime('%-I:%M%p')
        elif isinstance(self.start, date):
            times = 'All Day'
        else:
            times = 'Unknown'
            
        return f'<{self.title} ({self.id}) | {day} @ {times}>'

load_dotenv()

NTFY_TOPIC = os.getenv('NTFY_TOPIC')
CALENDAR_ID = os.getenv("CALENDAR_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")

SCOPES = ['https://www.googleapis.com/auth/calendar']

creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the "Service" Object
service = build('calendar', 'v3', credentials=creds)

def get_events_for_day(target_date: date) -> list[Event]:
    """Get all events that occur on this date

    Args:
        target_date (date): Date we want to get events for

    Returns:
        list[Event]: List of events; can be empty list
    """
    local_tz = ZoneInfo(TIMEZONE)

    # Create 'aware' datetimes for the start and end of the day
    # This automatically calculates the correct offset (e.g., -06:00 or -05:00)
    day_start_dt = datetime.combine(target_date, time.min, tzinfo=local_tz)
    day_end_dt = day_start_dt + timedelta(days=1)

    # Convert to ISO format
    time_min = day_start_dt.isoformat()
    time_max = day_end_dt.isoformat()

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    items = events_result.get('items', [])
    
    events: list[Event] = []
    
    for item in items:
        id = item.get("id", None)
        title = item.get("summary", "")
        description = item.get("description", "")
        
        start_node = item.get("start", {})
        end_node = item.get("end", {})
        
        if 'date' in start_node:
            start = date.fromisoformat(start_node.get('date'))
            end = date.fromisoformat(end_node.get('date'))
            is_all_day = True
        else:
            start = datetime.fromisoformat(start_node.get('dateTime'))
            end = datetime.fromisoformat(end_node.get('dateTime'))
            is_all_day = False

        event = Event(is_all_day, id, title, description, start, end)
        events.append(event)
    return events

def create_event(event: Event) -> None:
    """Create event on the calendar

    Args:
        event (Event): Event to add

    Raises:
        ValueError: If event already has an id
    """
    if event.id is not None:
        raise ValueError("Event already has an id; did you mean to update it?")

    event_body = {
        'summary': event.title,
        'description': event.description,
        'start': {},
        'end': {},
    }
    
    if event.is_all_day:
        time_field = "date"
    else:
        time_field = "dateTime"
        event_body["start"]["timeZone"] = TIMEZONE
        event_body["end"]["timeZone"] = TIMEZONE
        
    event_body["start"][time_field] = event.start.isoformat()
    if isinstance(event.end, (datetime, date)):
        event_body["end"][time_field] = event.end.isoformat()
    else:
        raise RuntimeError('Event.end is not datetime or date', event)

    e = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event_body
    ).execute()
    
    event.id = e.get("id")

def delete_event(event: Event):
    """Delete event from the calendar

    Args:
        event (Event): Event to delete from calendar; must have id
    """
    service.events().delete(
        calendarId=CALENDAR_ID,
        eventId=event.id
    ).execute()
    
    event.id = None
    
def update_event(event: Event) -> None:
    """Update event on the calendar

    Args:
        event (Event): Event to update; must have id

    Raises:
        ValueError: If event does not have id
    """
    if event.id is None:
        raise ValueError("Cannot update event without an id")

    # Fetch existing event to avoid wiping fields
    existing = service.events().get(
        calendarId=CALENDAR_ID,
        eventId=event.id
    ).execute()

    # Update common fields
    existing["summary"] = event.title
    existing["description"] = event.description

    # Update time fields
    if event.is_all_day:
        existing["start"] = {"date": event.start.isoformat()}
        if isinstance(event.end, (datetime, date)):
            existing["end"] = {"date": event.end.isoformat()}
        else:
            raise RuntimeError('Event.end is not datetime or date', event)
    else:
        existing["start"] = {
            "dateTime": event.start.isoformat(),
            "timeZone": TIMEZONE,
        }
        if isinstance(event.end, (datetime, date)):
            existing["end"] = {
                "dateTime": event.end.isoformat(),
                "timeZone": TIMEZONE,
            }
        else:
            raise RuntimeError('Event.end is not datetime or date', event)

    service.events().update(
        calendarId=CALENDAR_ID,
        eventId=event.id,
        body=existing
    ).execute()

# def sync_day(day: date, entries: list[Entry]) -> bool:
#     modified: bool = False
    
#     current_events = get_events_for_day(day)
    
#     matched_event_ids = set()
#     matched_entries = []
#     has_closed_event = False

#     # 1. Identify what matches and what is an "All Day" event
#     for event in current_events:
#         start_node = event.get('start', {})
        
#         # Check if it's an All-Day event (has 'date' instead of 'dateTime')
#         if 'date' in start_node:
#             if "Closed" in event.get('summary', ''):
#                 has_closed_event = True
#                 if not entries:
#                     matched_event_ids.add(event['id'])
#             continue

#         # Timed Event Logic
#         try:
#             g_start = datetime.fromisoformat(start_node.get('dateTime')).time()
#             g_end = datetime.fromisoformat(event.get('end', {}).get('dateTime')).time()
            
#             for entry in entries:
#                 if g_start == entry.start_time and g_end == entry.end_time:
#                     matched_entries.append(entry)
#                     matched_event_ids.add(event['id'])
#                     break
#         except (TypeError, ValueError):
#             continue

#     # 2. Delete Stale Events
#     # Anything in current_events that wasn't matched above
#     for event in current_events:
#         if event['id'] not in matched_event_ids:
#             delete_event(event['id'])
#             modified = True

#     # 3. Handle "Closed" (No entries)
#     if not entries:
#         if not has_closed_event:
#             create_all_day_event('CRWC Competition Pool: Closed', day)
#             modified = True
#             return True
#         return False

#     # 4. Add New Events
#     # Filter out entries that were already matched
#     new_entries = [e for e in entries if e not in matched_entries]
    
#     local_tz = ZoneInfo(TIMEZONE)
#     for entry in new_entries:
#         start_dt = datetime.combine(day, entry.start_time, tzinfo=local_tz)
#         end_dt = datetime.combine(day, entry.end_time, tzinfo=local_tz)
#         create_event(entry.info, start_dt.isoformat(), end_dt.isoformat())
#         modified = True
    
#     return modified