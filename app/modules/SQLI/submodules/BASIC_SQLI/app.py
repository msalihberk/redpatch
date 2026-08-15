import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("vulnerable.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
                   CREATE TABLE users
                   (
                       id       INTEGER PRIMARY KEY AUTOINCREMENT,
                       username TEXT,
                       password TEXT,
                       role     TEXT
                   )
                   """)
    # Örnek kullanıcılar
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES ('admin', 'SuperSecretPass123!', 'administrator')")
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('john', 'password123', 'user')")
    conn.commit()
    conn.close()


# ZAFİYETLİ ENDPOINT (String Formatlama ile SQLi)
@app.route("/login-vulnerable", methods=["POST"])
def login_vulnerable():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    conn = sqlite3.connect("vulnerable.db")
    cursor = conn.cursor()

    # Zafiyetli sorgu: Kullanıcı girdisi doğrudan sorguya ekleniyor
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}'"

    try:
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({
                "status": "success",
                "message": "Giriş başarılı!",
                "user": {"id": user[0], "username": user[1], "role": user[2]},
                "executed_query": query
            }), 200
        else:
            return jsonify(
                {"status": "fail", "message": "Geçersiz kullanıcı adı veya şifre.", "executed_query": query}), 401
    except sqlite3.Error as e:
        conn.close()
        return jsonify({"status": "error", "error": str(e), "executed_query": query}), 400


# GÜVENLİ ENDPOINT (Parameterized Query)
@app.route("/login-fixed", methods=["POST"])
def login_fixed():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    conn = sqlite3.connect("vulnerable.db")
    cursor = conn.cursor()

    # Güvenli sorgu: Parametrik sorgu (Prepared Statement)
    query = "SELECT id, username, role FROM users WHERE username = ? AND password = ?"

    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "message": "Giriş başarılı!",
            "user": {"id": user[0], "username": user[1], "role": user[2]}
        }), 200
    else:
        return jsonify({"status": "fail", "message": "Geçersiz kullanıcı adı veya şifre."}), 401


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
    