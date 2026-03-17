import sqlite3
import bcrypt
import os

# ---------------- SETTINGS ----------------
DB_FILE = "users.db"

# ---------------- CONNECT ----------------
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()


# Users table
c.execute("""
DELETE FROM users WHERE id BETWEEN 20 AND 1590;
""")


conn.commit()

# ---------------- EXAMPLE FUNCTIONS ----------------
conn.close()
