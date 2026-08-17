import sqlite3
import uvicorn
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from codes.vulnerables.target_snippet import authenticate_user as vulnerable_authenticate_user
from codes.solutions.solution_snippet import authenticate_user as secure_authenticate_user

app = FastAPI(title="SQL Injection Lab Submodule")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def init_db():
    conn = sqlite3.connect(BASE_DIR / "vulnerable.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
        CREATE TABLE users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role     TEXT
        )
    """)
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES ('admin', 'SuperSecretPass123!', 'administrator')"
    )
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES ('john', 'password123', 'user')"
    )
    conn.commit()
    conn.close()


init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"result": None})


def responds_with_html(request: Request) -> bool:
    """Return the lab UI after a browser form navigation into the iframe."""
    return "text/html" in request.headers.get("accept", "").lower()


def login_response(request: Request, result: dict, status_code: int):
    if responds_with_html(request):
        return templates.TemplateResponse(
            request,
            "index.html",
            {"result": result, "result_status_code": status_code},
            status_code=status_code,
        )
    return JSONResponse(status_code=status_code, content=result)


@app.post("/login-vulnerable")
async def login_vulnerable(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    user, query, conn = vulnerable_authenticate_user(username, password)

    try:
        if user:
            return login_response(
                request,
                {
                    "status": "success",
                    "message": "Authentication successful!",
                    "user": {"id": user[0], "username": user[1], "role": user[2]},
                    "executed_query": query,
                },
                status.HTTP_200_OK,
            )
        return login_response(
            request,
            {
                "status": "fail",
                "message": "Invalid username or password.",
                "executed_query": query,
            },
            status.HTTP_401_UNAUTHORIZED,
        )
    except sqlite3.Error as e:
        return login_response(
            request,
            {
                "status": "error",
                "error": str(e),
                "executed_query": query,
            },
            status.HTTP_400_BAD_REQUEST,
        )
    finally:
        conn.close()


@app.post("/login-fixed")
async def login_fixed(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    user, query, conn = secure_authenticate_user(username, password)

    if user:
        return login_response(
            request,
            {
                "status": "success",
                "message": "Authentication successful!",
                "user": {"id": user[0], "username": user[1], "role": user[2]},
            },
            status.HTTP_200_OK,
        )
    return login_response(
        request,
        {"status": "fail", "message": "Invalid username or password."},
        status.HTTP_401_UNAUTHORIZED,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
