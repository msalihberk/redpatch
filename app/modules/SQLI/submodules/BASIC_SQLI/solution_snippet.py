import sqlite3

def authenticate_user(username, password):
    """Güvenli Kimlik Doğrulama Fonksiyonu.

    Parametrik sorgu (Prepared Statements) kullanılarak SQL Injection önlenmiştir.
    """
    conn = sqlite3.connect("vulnerable.db")
    cursor = conn.cursor()

    # GÜVENLİ YAPI:
    # Veriler sorgu yapısından ayrı tutulur ve veritabanı sürücüsü tarafından sanitize edilir.
    query = "SELECT id, username, role FROM users WHERE username = ? AND password = ?"

    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()
    return user
