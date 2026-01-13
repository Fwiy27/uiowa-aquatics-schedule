from src.google_calendar import get_events_for_day, create_event, delete_event, sync_day
from src.scraper import get_entries
from datetime import date


day = date(2026, 1, 19)

entries = get_entries(day)

if entries:
    sync_day(day, entries)