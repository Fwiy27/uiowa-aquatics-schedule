from src.scraper import get_times
from datetime import date, timedelta
import calendar

date_times: list[tuple] = []

start_date = date.today()
next_month = (start_date.month % 12) + 1
next_year = start_date.year + (start_date.month // 12)
_, last_day_num = calendar.monthrange(next_year, next_month)
end_date = date(next_year, next_month, last_day_num)

current_date = start_date
while current_date <= end_date:
    date_times.append((current_date, get_times(current_date)))
    current_date += timedelta(days=1)
    
for day, md in date_times:
    print(f"# {day.strftime('%A')} | {day}")
    print(md, '\n')