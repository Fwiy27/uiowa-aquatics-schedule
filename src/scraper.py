import cloudscraper
import re

from requests import Response
from bs4 import BeautifulSoup
from tabulate import tabulate
from datetime import date, time, datetime
from dataclasses import dataclass

@dataclass
class Entry:
    status: str
    start_time: time
    end_time: time
    info: str

    def to_tuple(self) -> tuple:
        # 1. noon object for comparison
        noon = time(12, 0)
        
        # 2. Logic for color coding based on noon cross-over
        if self.start_time < noon and self.end_time <= noon:
            color = '#5CE65C' # All Morning
        elif self.start_time < noon and self.end_time > noon:
            color = '#FFBF00' # Crosses Noon
        else:
            color = '#FF2A00' # All Afternoon
            
        # 3. Formatting the string
        # Note: %I is for 12-hour clock (5:30pm), %H is for 24-hour clock (17:30)
        fmt = '%-I:%M%p'
        time_str = f"%{color}% {self.start_time.strftime(fmt).lower()} - {self.end_time.strftime(fmt).lower()} %%"
        
        return (self.status, time_str, self.info)
        


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

scraper = cloudscraper.create_scraper()
scraper.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "HX-Request": "true",  # Enable HTMX/JSON responses
})

def get_response(date: date) -> Response:
    URL = "https://recserv.uiowa.edu/aquatics"
    
    json = {
        "date": date.isoformat(),
        "form_id": "uiowa_hours_filter_form_1",
    }

    params = {
        "ajax_form": 1
    }

    response = scraper.post(URL, params=params, data=json)
    
    response.raise_for_status()
    
    return response

def parse_response(response: Response) -> dict:
    commands: dict = response.json()
    
    # Get the first command that is an 'insert' and has a 'data' key
    insert_command: dict | None = next((command for command in commands if command.get('command', '') == 'insert' and 'data' in command), None)
    
    # Error if no valid command is found
    if not insert_command:
        raise RuntimeError("No valid command found", commands)
    
    return insert_command

def get_times_list(insert_command: dict) -> list[Entry] | None:
    times: list[Entry] = []
    soup = BeautifulSoup(insert_command.get("data", ""), "html.parser")

    item_list = soup.find("div", class_="item-list")
    if not item_list:
        return None
    
    li_list = item_list.find_all("li")
    
    for li in li_list:
        badge = li.find(class_="badge")
        if not badge:
            raise RuntimeError('badge not found', li)
        status = badge.text
        
        # Parse times with regex
        raw_text: str = li.text
        regex_times = re.findall(r'\d{1,2}:\d{2}(?:am|pm)', raw_text)
        start_time = datetime.strptime(regex_times[0], '%I:%M%p').time()
        end_time = datetime.strptime(regex_times[1], '%I:%M%p').time()
        
        # Get other info from raw_text
        info = raw_text.split("-")[-1].strip()
        
        # Append entry to list
        times.append(Entry(status, start_time, end_time, info))
    return times

def to_markdown(times: list[Entry] | None, format: str = "github") -> str:
    if not times:
        return "!!! danger Closed\n\tCRWC Competition Pool is closed this day"
    headers = ["Status", "Time", "Info"]
    table = tabulate([t.to_tuple() for t in times], headers=headers, tablefmt=format)
    return table

def get_times(date: date) -> str:
    response = get_response(date)
    insert_command = parse_response(response)
    times_list = get_times_list(insert_command)
    markdown = to_markdown(times_list)
    
    return markdown