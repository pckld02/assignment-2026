import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
import os
import time
import re

INPUT_FILE = "manufacturer_links.txt"
OUTPUT_ROOT = "output"

HEADERS = {"User-Agent": "Mozilla/5.0"}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.headers.update(HEADERS)

# -------------------------

def safe_get(url):
    return session.get(url, verify=False, timeout=30)

def clean_filename(text):
    """Make safe folder/file names"""
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]+", "", text)
    text = text.replace(" ", "_")
    return text

def extract_text(td):
    if not td:
        return ""
    return td.get_text(separator="\n", strip=True)

def get_disc_links(start_url):

    links = set()

    r = safe_get(start_url)
    soup = BeautifulSoup(r.text, "html.parser")

    for td in soup.find_all("td", class_="col0"):
        a = td.find("a")
        if a and a.get("href"):
            links.add(urljoin(start_url, a["href"]))

    return links

def create_unique_folder(base_folder, name):

    folder = os.path.join(base_folder, name)

    if not os.path.exists(folder):
        return folder

    i = 2
    while True:
        new_folder = f"{folder}_{i}"
        if not os.path.exists(new_folder):
            return new_folder
        i += 1

def scrape_disc_page(disc_url, brand_folder):

    print("   ->", disc_url)

    r = safe_get(disc_url)
    soup = BeautifulSoup(r.text, "html.parser")

    box = soup.find("div", class_="plugin_wrap")
    if not box:
        print("      ❌ No data box")
        return

    table = box.find("table")

    fields = {
        "Brand": "",
        "Series": "",
        "SKU": "",
        "Capacity": "",
        "Color": "",
        "Manufactured by": "",
        "Made in": "",
        "Notes": ""
    }

    if table:
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue

            key = th.get_text(strip=True)
            if key in fields:
                fields[key] = extract_text(td)

    # ---- CREATE UNIQUE FOLDER NAME ----

    brand = clean_filename(fields["Brand"] or "unknown_brand")
    series = clean_filename(fields["Series"] or "unknown_series")
    capacity = clean_filename(fields["Capacity"] or "unknown")

    folder_name = f"{brand}_{series}_{capacity}"
    disc_folder = create_unique_folder(brand_folder, folder_name)

    os.makedirs(disc_folder, exist_ok=True)

    # ---- SAVE TEXT ----

    txt_path = os.path.join(disc_folder, f"{folder_name}.txt")

    with open(txt_path, "w", encoding="utf-8") as f:
        for k, v in fields.items():
            f.write(f"{k}: {v}\n")

    # ---- DOWNLOAD IMAGES ----

    images = box.find_all("a", class_="media")

    for i, img in enumerate(images):

        href = img.get("href")
        if not href:
            continue

        img_url = urljoin(disc_url, href)

        try:
            img_data = safe_get(img_url).content
            ext = img_url.split(".")[-1].split("?")[0]

            img_file = os.path.join(disc_folder, f"image_{i+1}.{ext}")

            with open(img_file, "wb") as f:
                f.write(img_data)

        except Exception as e:
            print("      ❌ Image error:", e)

# -------------------------

def main():

    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        manufacturer_urls = [line.strip() for line in f if line.strip()]

    for manufacturer_url in manufacturer_urls:

        brand_slug = manufacturer_url.rstrip("/").split("/")[-2]
        start_url = f"https://www.minidisc.wiki/discs/{brand_slug}/start"

        print("\n====== BRAND:", brand_slug, "======")

        brand_folder = os.path.join(OUTPUT_ROOT, brand_slug)
        os.makedirs(brand_folder, exist_ok=True)

        disc_links = get_disc_links(start_url)

        print(" Found", len(disc_links), "discs")

        for disc_url in sorted(disc_links):
            scrape_disc_page(disc_url, brand_folder)
            time.sleep(0.3)

if __name__ == "__main__":
    main()
