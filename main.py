from src.google_calendar import sync_day
from src.scraper import get_entries
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import calendar
import requests
import os


load_dotenv()

NTFY_TOPIC = os.getenv('NTFY_TOPIC')
TIMEZONE = os.getenv('TIMEZONE', 'America/Chicago')

# TODAY
from_day = datetime.now(ZoneInfo(TIMEZONE)).date()
current_month, current_year = from_day.month, from_day.year
to_month = (current_month) % 12 + 1
to_year = current_year if to_month != 1 else current_year + 1
# LAST DAY OF THE NEXT MONTH
to_day = date(year=to_year, month=to_month, day=1)
_, last_day_num = calendar.monthrange(to_day.year, to_day.month)
to_day = to_day.replace(day=last_day_num)

print(f'Managing events from {from_day.isoformat()} to {to_day.isoformat()}')

notifications: list[str] = []

current_date = from_day
while current_date <= to_day:
    print(current_date.isoformat())
    entries = get_entries(current_date)

    notification = sync_day(current_date, entries)
    if notification:
        print(f'\t{notification}')
        notifications.append(f'{current_date.isoformat()}: {notification}')

    current_date += timedelta(days=1)

if notifications:
    headers = {
        'Title': 'Updated UIOWA Aquatic Calendar'
    }

    try:
        response = requests.post(f'https://ntfy.sh/{NTFY_TOPIC}', data='\n'.join(notifications), headers=headers)
        response.raise_for_status()
    except:
        print('Error notifying with ntfy')