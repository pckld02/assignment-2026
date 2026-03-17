import sqlite3
import bcrypt
import os

# ---------------- SETTINGS ----------------
DB_FILE = "users.db"

# ---------------- CONNECT ----------------
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# Enable foreign key support
c.execute("PRAGMA foreign_keys = ON")

# ---------------- TABLES ----------------

# Users table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL,
    profile_picture TEXT
)
""")

# Collections table
c.execute("""
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# Favorite discs table (many-to-many)
c.execute("""
CREATE TABLE IF NOT EXISTS favorite_discs (
    user_id INTEGER NOT NULL,
    disc_id INTEGER NOT NULL,
    PRIMARY KEY(user_id, disc_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(disc_id) REFERENCES discs(id)  -- assumes you have a discs table
)
""")

# Favorite collections table (many-to-many)
c.execute("""
CREATE TABLE IF NOT EXISTS favorite_collections (
    user_id INTEGER NOT NULL,
    collection_id INTEGER NOT NULL,
    PRIMARY KEY(user_id, collection_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(collection_id) REFERENCES collections(id)
)
""")

conn.commit()

# ---------------- EXAMPLE FUNCTIONS ----------------

def hash_password(password):
    """Hash a password for storing"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed

def add_user(username, name, password, profile_picture=None):
    """Add a user to the database"""
    password_hash = hash_password(password)
    c.execute("""
        INSERT INTO users (username, name, password_hash, profile_picture)
        VALUES (?, ?, ?, ?)
    """, (username, name, password_hash, profile_picture))
    conn.commit()
    return c.lastrowid

# Example usage
if __name__ == "__main__":
    # Ensure folder for profile pictures exists
    os.makedirs("profile_pictures", exist_ok=True)

    # Add a test user
    user_id = add_user(
        username="johndoe",
        name="John Doe",
        password="supersecret123",
        profile_picture="profile_pictures/johndoe.png"
    )
    print(f"Created user with ID {user_id}")

    # Close connection
    conn.close()
