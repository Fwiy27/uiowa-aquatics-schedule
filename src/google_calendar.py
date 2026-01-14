from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import date, datetime, time, timedelta
from src.scraper import Entry
from dotenv import load_dotenv

import requests
import os

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

def get_events_for_day(target_date: date) -> list:
    local_tz = ZoneInfo(TIMEZONE)

    # Create 'aware' datetimes for the start and end of the day
    # This automatically calculates the correct offset (e.g., -06:00 or -05:00)
    day_start_dt = datetime.combine(target_date, time.min, tzinfo=local_tz)
    day_end_dt = day_start_dt + timedelta(days=1)

    # Convert to ISO format (Google will see the -06:00 offset and understand)
    time_min = day_start_dt.isoformat()
    time_max = day_end_dt.isoformat()

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])

def create_event(summary, start_time_iso, end_time_iso):
    event_body = {
        'summary': summary,
        'start': {'dateTime': start_time_iso, 'timeZone': TIMEZONE},
        'end': {'dateTime': end_time_iso, 'timeZone': TIMEZONE},
    }
    
    event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
    print(f"Event created: {event.get('htmlLink')}")

from datetime import timedelta, date

def create_all_day_event(summary, target_date: date):
    # End date must be the day AFTER the event for it to show as a single day
    end_date = target_date + timedelta(days=1)
    
    event_body = {
        'summary': summary,
        'start': {
            'date': target_date.isoformat(), # Result: '2026-01-13'
        },
        'end': {
            'date': end_date.isoformat(),    # Result: '2026-01-14'
        },
    }
    
    event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
    print(f"All-day event created: {event.get('htmlLink')}")
    
def delete_event(event_id):
    try:
        service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        print(f"Successfully deleted event: {event_id}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
def sync_day(day: date, entries: list[Entry]) -> bool:
    modified: bool = False
    
    current_events = get_events_for_day(day)
    
    matched_event_ids = set()
    matched_entries = []
    has_closed_event = False

    # 1. Identify what matches and what is an "All Day" event
    for event in current_events:
        start_node = event.get('start', {})
        
        # Check if it's an All-Day event (has 'date' instead of 'dateTime')
        if 'date' in start_node:
            if "Closed" in event.get('summary', ''):
                has_closed_event = True
                if not entries:
                    matched_event_ids.add(event['id'])
            continue

        # Timed Event Logic
        try:
            g_start = datetime.fromisoformat(start_node.get('dateTime')).time()
            g_end = datetime.fromisoformat(event.get('end', {}).get('dateTime')).time()
            
            for entry in entries:
                if g_start == entry.start_time and g_end == entry.end_time:
                    matched_entries.append(entry)
                    matched_event_ids.add(event['id'])
                    break
        except (TypeError, ValueError):
            continue

    # 2. Delete Stale Events
    # Anything in current_events that wasn't matched above
    for event in current_events:
        if event['id'] not in matched_event_ids:
            delete_event(event['id'])
            modified = True

    # 3. Handle "Closed" (No entries)
    if not entries:
        if not has_closed_event:
            create_all_day_event('CRWC Competition Pool: Closed', day)
            modified = True
            return True
        return False

    # 4. Add New Events
    # Filter out entries that were already matched
    new_entries = [e for e in entries if e not in matched_entries]
    
    local_tz = ZoneInfo(TIMEZONE)
    for entry in new_entries:
        start_dt = datetime.combine(day, entry.start_time, tzinfo=local_tz)
        end_dt = datetime.combine(day, entry.end_time, tzinfo=local_tz)
        create_event(entry.info, start_dt.isoformat(), end_dt.isoformat())
        modified = True
    
    return modified