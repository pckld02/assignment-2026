import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import urllib3
import os
import time
import re
import sqlite3

# ---------------- SETTINGS ----------------

INPUT_FILE = "manufacturer_links.txt"
OUTPUT_ROOT = "output"
DB_FILE = "minidisc.db"

HEADERS = {"User-Agent": "Mozilla/5.0"}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.headers.update(HEADERS)

# ---------------- DATABASE ----------------

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Create tables
c.execute("""
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS discs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER,
    name TEXT,
    series TEXT,
    sku TEXT,
    capacity TEXT,
    color TEXT,
    manufactured_by TEXT,
    made_in TEXT,
    notes TEXT,
    FOREIGN KEY (brand_id) REFERENCES brands(id)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disc_id INTEGER,
    url TEXT,
    file_path TEXT,
    FOREIGN KEY (disc_id) REFERENCES discs(id)
)
""")
conn.commit()

# ------------- HELPER FUNCTIONS -------------

def safe_get(url):
    """Request with SSL verification disabled"""
    return session.get(url, verify=False, timeout=30)

def clean_filename(text):
    """Sanitize folder/file names"""
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]+", "", text)
    text = text.replace(" ", "_")
    return text

def extract_text(td):
    if not td:
        return ""
    return td.get_text(separator="\n", strip=True)

def get_or_create_brand(conn, brand_name):
    c = conn.cursor()
    c.execute("SELECT id FROM brands WHERE name=?", (brand_name,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute("INSERT INTO brands (name) VALUES (?)", (brand_name,))
    conn.commit()
    return c.lastrowid

def insert_disc(conn, brand_id, fields, disc_name):
    c = conn.cursor()
    c.execute("""
        INSERT INTO discs
        (brand_id, name, series, sku, capacity, color, manufactured_by, made_in, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        brand_id,
        disc_name,
        fields.get("Series", ""),
        fields.get("SKU", ""),
        fields.get("Capacity", ""),
        fields.get("Color", ""),
        fields.get("Manufactured by", ""),
        fields.get("Made in", ""),
        fields.get("Notes", "")
    ))
    conn.commit()
    return c.lastrowid

def insert_image(conn, disc_id, url, file_path):
    c = conn.cursor()
    c.execute("""
        INSERT INTO images (disc_id, url, file_path)
        VALUES (?, ?, ?)
    """, (disc_id, url, file_path))
    conn.commit()

def get_disc_links(start_url):
    """Get all disc links from brand start page"""
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

    # -------- CREATE UNIQUE DISC FOLDER --------
    brand = clean_filename(fields["Brand"] or "unknown_brand")
    series = clean_filename(fields["Series"] or "unknown_series")
    capacity = clean_filename(fields["Capacity"] or "unknown")
    folder_name = f"{brand}_{series}_{capacity}"
    disc_folder = create_unique_folder(brand_folder, folder_name)
    os.makedirs(disc_folder, exist_ok=True)

    # -------- INSERT INTO DATABASE --------
    brand_id = get_or_create_brand(conn, fields["Brand"] or "Unknown")
    disc_id = insert_disc(conn, brand_id, fields, folder_name)

    # -------- DOWNLOAD IMAGES --------
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
            insert_image(conn, disc_id, img_url, img_file)
        except Exception as e:
            print("      ❌ Image error:", e)

# ---------------- MAIN ----------------

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

        try:
            disc_links = get_disc_links(start_url)
            print(" Found", len(disc_links), "discs")

            for disc_url in sorted(disc_links):
                scrape_disc_page(disc_url, brand_folder)
                time.sleep(0.3)  # be polite
        except Exception as e:
            print("❌ Brand error:", e)

if __name__ == "__main__":
    main()
