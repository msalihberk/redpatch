import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "vulnerable.db"

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT id, username, role FROM users WHERE username = ? AND password = ?"

    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()
    return user, query, conn
