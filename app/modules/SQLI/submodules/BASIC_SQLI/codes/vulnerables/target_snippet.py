import sqlite3

def authenticate_user(username, password):
    """
    Vulnerable Authentication Function.
    Data received from the user is formatted and inserted directly into an SQL query.
    """
    conn = sqlite3.connect("../../vulnerable.db")
    cursor = conn.cursor()

    # SQL INJECTION VULNERABILITY:
    # The input from the user is directly formatted into the SQL query.
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"

    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user, query, conn
