from src.google_calendar import get_events_for_day, create_event, delete_event, sync_day
from src.scraper import get_entries
from datetime import date, timedelta

from_day = date.today()
to_day = from_day + timedelta(days=14)

current_date = from_day

while current_date < to_day:
    entries = get_entries(current_date)

    entries = entries or []
    
    sync_day(current_date, entries)
        
    current_date += timedelta(days=1)