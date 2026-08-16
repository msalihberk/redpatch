import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "vulnerable.db"

def authenticate_user(username, password):
    """
    Vulnerable Authentication Function.
    Data received from the user is formatted and inserted directly into an SQL query.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # SQL INJECTION VULNERABILITY:
    # The input from the user is directly formatted into the SQL query.
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"

    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user, query, conn
