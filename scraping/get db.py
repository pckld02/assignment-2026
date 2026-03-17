import requests
from bs4 import BeautifulSoup

url = "https://www.minidisc.wiki/discs/sorting/list"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

# find table
table = soup.find("table")

rows = table.find_all("tr")

data = []

for row in rows:
    cols = row.find_all("td")
    if not cols:
        continue

    # adjust indexes depending on actual columns
    name = cols[0].get_text(strip=True)

    img = row.find("img")
    img_url = img["src"] if img else None

    duration = cols[2].get_text(strip=True) if len(cols) > 2 else ""

    data.append({
        "name": name,
        "duration": duration,
        "image": img_url
    })

print(data)
