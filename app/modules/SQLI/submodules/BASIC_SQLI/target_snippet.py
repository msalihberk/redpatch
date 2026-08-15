import sqlite3

def authenticate_user(username, password):
    """Zafiyetli Kimlik Doğrulama Fonksiyonu.

    Kullanıcıdan alınan veriler doğrudan SQL sorgusuna formatlanarak eklenmektedir.
    """
    conn = sqlite3.connect("vulnerable.db")
    cursor = conn.cursor()

    # SQL INJECTION ZAFİYETİ:
    # 'admin' OR '1'='1' girdisi ile sorgu bypass edilebilir.
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"

    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user
