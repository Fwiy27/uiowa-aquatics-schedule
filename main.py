from src.scraper import get_times
from datetime import date, timedelta

date_times: list[tuple] = []

start_date = date.today()
end_date = start_date + timedelta(days=7)  # 1 week from now

current_date = start_date
while current_date <= end_date:
    date_times.append((current_date, get_times(current_date)))
    current_date += timedelta(days=1)
    
for day, md in date_times:
    print(f"# {day.strftime('%A')} | {day}")
    print(md, '\n')