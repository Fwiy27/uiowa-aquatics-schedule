import cloudscraper

from bs4 import BeautifulSoup
from tabulate import tabulate

URL = "https://recserv.uiowa.edu/aquatics"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

scraper = cloudscraper.create_scraper()
scraper.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "HX-Request": "true",  # Enable HTMX/JSON responses
})

# response = scraper.get(URL)

# soup = BeautifulSoup(response.content, "html.parser")

# print(response.text)
# print(soup)
headers = {"Referer": URL}

json = {
    "date": "2026-01-20",
    "form_id": "uiowa_hours_filter_form_1",
}

params = {
    "ajax_form": 1
}

response = scraper.post(URL, params=params, data=json)

commands = response.json()

commands = [command for command in commands if command.get("command") == "insert"]

main_command = commands[0]

if not (main_command.get("data", None)):
    raise RuntimeError("No data in the insert command")
soup = BeautifulSoup(main_command.get("data"), "html.parser")

item_list = soup.find("div", class_="item-list")
if not item_list:
    raise RuntimeError("item-list not found")
li_list = item_list.find_all("li")

times = []
for li in li_list:
    badge = li.find(class_="badge")
    time = li.text
    if not badge or not time:
        raise RuntimeError("Badge or Time not found", badge, time)
    times.append((badge.text, time))
    
print(tabulate(times, headers=['Status', 'Description'], tablefmt='github'))