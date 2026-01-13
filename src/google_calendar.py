from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from datetime import date, datetime, time, timedelta
from src.scraper import Entry

import os

load_dotenv()

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
        
def sync_day(day: date, entries: list[Entry]):
    events_to_remove: list[dict] = []
    entries_to_remove: list[Entry] = []
    
    current_events = get_events_for_day(day)
    for event in current_events:
        start_time = datetime.fromisoformat(event.get('start').get('dateTime')).time()
        end_time = datetime.fromisoformat(event.get('end').get('dateTime')).time()
        for entry in entries:
            if start_time == entry.start_time and end_time == entry.end_time:
                entries_to_remove.append(entry)
                events_to_remove.append(event)
    
    if not entries:
        for event in current_events:
            delete_event(event.get('id'))
        create_all_day_event('CRWC Competition Pool: Closed', day)
        return 
    
    # Remove from entries and current_events
    for e in entries_to_remove:
        entries.remove(e)
    for e in events_to_remove:
        current_events.remove(e)
    
    # If any events are left in current_events then they are outdated and need to be removed
    for event in current_events:
        delete_event(event.get('id'))
        
    # Now we can add the new events
    local_tz = ZoneInfo(TIMEZONE)
    
    for entry in entries:
        start_time = datetime.combine(day, entry.start_time, tzinfo=local_tz)
        end_time = datetime.combine(day, entry.end_time, tzinfo=local_tz)
        
        create_event(entry.info, start_time.isoformat(), end_time.isoformat())