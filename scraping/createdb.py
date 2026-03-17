import sqlite3
import os

DB_FILE = "minidisc.db"

# Create DB and tables if not exist
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

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
