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
    
    def __repr__(self) -> str:
        return f'<{self.status}, {self.start_time.strftime('%I-%M%p')}-{self.end_time.strftime('%I-%M%p')} >'

    def hash(self) -> str:
        return f'{self.status}{self.start_time.isoformat()}{self.end_time.isoformat()}{self.info}'
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

scraper = cloudscraper.create_scraper()
scraper.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "HX-Request": "true",  # Enable HTMX/JSON responses
})

def get_entries(date: date) -> list[Entry] | None:
    URL = "https://recserv.uiowa.edu/aquatics"
    
    payload = {
        "date": date.isoformat(),
        "form_id": "uiowa_hours_filter_form_1",
    }

    response_parameters = {
        "ajax_form": 1
    }

    response = scraper.post(URL, params=response_parameters, data=payload)
    
    response.raise_for_status()
    
    commands: dict = response.json()
    
    # Get the first command that is an 'insert' and has a 'data' key
    # Error if no valid command is found
    insert_command: dict | None = next((command for command in commands if command.get('command', '') == 'insert' and 'data' in command), None)
    if not insert_command:
        raise RuntimeError("No valid command found", commands)
    
    soup = BeautifulSoup(insert_command.get("data", ""), "html.parser")

    item_list = soup.find("div", class_="item-list")
    if not item_list:
        return None
    
    li_list = item_list.find_all("li")
    
    entries: list[Entry] = []
    
    for li in li_list:
        badge = li.find(class_="badge")
        if not badge:
            raise RuntimeError('badge not found', li)
        status = badge.text
        
        # Parse times with regex
        regex_times = re.findall(r'\d{1,2}:\d{2}(?:am|pm)', li.text)
        if len(regex_times) != 2:
            raise RuntimeError("2 times not found", li.text)
        start_time = datetime.strptime(regex_times[0], '%I:%M%p').time()
        end_time = datetime.strptime(regex_times[1], '%I:%M%p').time()
        
        # Get other info from raw_text
        info = li.text.split("-")[-1].strip()
        
        # Append entry to list
        entries.append(Entry(status, start_time, end_time, info))
    return entries