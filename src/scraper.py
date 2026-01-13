import cloudscraper
import re

from requests import Response
from bs4 import BeautifulSoup
from tabulate import tabulate
from datetime import date, time, datetime
from dataclasses import dataclass

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

def get_times_list(insert_command: dict) -> list[tuple] | None:
    times: list[tuple] = []
    soup = BeautifulSoup(insert_command.get("data", ""), "html.parser")

    item_list = soup.find("div", class_="item-list")
    if not item_list:
        return None
    
    li_list = item_list.find_all("li")
    
    for li in li_list:
        badge = li.find(class_="badge")
        raw_text: str = li.text
        
        regex_times = re.findall(r'\d{1,2}:\d{2}(?:am|pm)', raw_text)
        st, et = regex_times
        start_time = datetime.strptime(st, '%I:%M%p').time()
        end_time = datetime.strptime(et, '%I:%M%p').time()
        
        noon = time(12, 0)
        
        if start_time < noon and end_time < noon:
            color = '#5CE65C'
        elif start_time < noon and end_time > noon:
            color = '#FFBF00'
        else:
            color = '#FF2A00'
        
        time_str = f"%{color}% {regex_times[0]} - {regex_times[1]} %%"
        
        if not badge or not regex_times or not raw_text:
            raise RuntimeError("Badge or Time not found", badge, regex_times)
        
        status = badge.text
        info = raw_text.split("-")[-1].strip()
        
        times.append((status, time_str, info))
    return times

def to_markdown(times: list[tuple] | None, format: str = "github") -> str:
    if not times:
        return "!!! danger Closed\n\tCRWC Competition Pool is closed this day"
    headers = ["Status", "Time", "Info"]
    table = tabulate(times, headers=headers, tablefmt=format)
    return table

def get_times(date: date) -> str:
    response = get_response(date)
    insert_command = parse_response(response)
    times_list = get_times_list(insert_command)
    markdown = to_markdown(times_list)
    
    return markdown