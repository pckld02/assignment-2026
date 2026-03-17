import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3

# Disable SSL warnings (school network fix)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.minidisc.wiki/discs/sorting/manufacturer"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# Fetch page
response = requests.get(URL, headers=headers, verify=False)
soup = BeautifulSoup(response.text, "html.parser")

# Find UL container
brand_list = soup.find("ul", class_="fix-media-list-overlap")

links = []

if brand_list:
    for li in brand_list.find_all("li"):
        a = li.find("a")
        if a and a.get("href"):
            full_url = urljoin(URL, a["href"])
            links.append(full_url)

# Remove duplicates
links = list(dict.fromkeys(links))

# ---- SAVE TO TEXT FILE ----
filename = "manufacturer_links.txt"

with open(filename, "w", encoding="utf-8") as f:
    for link in links:
        f.write(link + "\n")

print(f"Saved {len(links)} links to {filename}")
