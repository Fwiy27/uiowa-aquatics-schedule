# from src.google_calendar import get_events_for_day, create_event, delete_event, sync_day
# from src.scraper import get_entries
# from datetime import date, timedelta
# import calendar
# import requests

# from dotenv import load_dotenv

# import requests
# import os

# load_dotenv()

# NTFY_TOPIC = os.getenv('NTFY_TOPIC')

# # TODAY
# from_day = date.today()
# # LAST DAY OF THE NEXT MONTH
# to_day = from_day + timedelta(days=32)
# _, last_day_num = calendar.monthrange(to_day.year, to_day.month)
# to_day = to_day.replace(day=last_day_num)

# print(f'Managing events from {from_day.isoformat()} to {to_day.isoformat()}')

# dates_modified = set()

# current_date = from_day
# while current_date <= to_day:
#     print(current_date.isoformat())
#     entries = get_entries(current_date)

#     entries = entries or []
    
#     modified = sync_day(current_date, entries)
#     if modified:
#         dates_modified.add(current_date)
        
#     current_date += timedelta(days=1)
    
# if dates_modified:
#     dates = [d.isoformat() for d in sorted(list(dates_modified))]
#     notification = '\n'.join(dates)
    
#     print('Dates modified: ' + ', '.join(dates))
    
#     headers = {
#         'title': 'Updated UIOWA Aquatic Calendar'
#     }
    
#     requests.post(f'http://ntfy.sh/{NTFY_TOPIC}', data=notification, headers=headers)

from src.google_calendar import get_events_for_day
from datetime import date

d = date(2026, 1, 14)

events = get_events_for_day(d)

for event in events:
    print(event)