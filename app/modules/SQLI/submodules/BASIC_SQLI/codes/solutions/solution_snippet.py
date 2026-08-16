import sqlite3

def authenticate_user(username, password):
    """
    Secure Authentication Function.
    SQL injection has been prevented by using prepared statements.
    """
    conn = sqlite3.connect("../../vulnerable.db")
    cursor = conn.cursor()

    # SECURE ARCHITECTURE:
    # Data is kept separate from the query structure and is sanitised by the database driver.
    query = "SELECT id, username, role FROM users WHERE username = ? AND password = ?"

    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()
    return user, query, conn
