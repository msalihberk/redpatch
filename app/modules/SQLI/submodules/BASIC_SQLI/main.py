import sqlite3
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from codes.vulnerables.target_snippet import authenticate_user as vulnerable_authenticate_user
from codes.solutions.solution_snippet import authenticate_user as secure_authenticate_user

app = FastAPI(title="SQL Injection Lab Submodule")

templates = Jinja2Templates(directory="app/templates")


class LoginPayload(BaseModel):
    username: str = ""
    password: str = ""


def init_db():
    conn = sqlite3.connect("vulnerable.db")
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
    return templates.TemplateResponse(request, "index.html")


@app.post("/login-vulnerable")
async def login_vulnerable(payload: LoginPayload):
    username = payload.username
    password = payload.password

    user, query, conn = vulnerable_authenticate_user(username, password)

    try:
        if user:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "success",
                    "message": "Authentication successful!",
                    "user": {"id": user[0], "username": user[1], "role": user[2]},
                    "executed_query": query,
                },
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "status": "fail",
                    "message": "Invalid username or password.",
                    "executed_query": query,
                },
            )
    except sqlite3.Error as e:
        conn.close()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "error": str(e),
                "executed_query": query,
            },
        )


@app.post("/login-fixed")
async def login_fixed(payload: LoginPayload):
    username = payload.username
    password = payload.password

    user, query, conn = secure_authenticate_user(username, password)

    if user:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Authentication successful!",
                "user": {"id": user[0], "username": user[1], "role": user[2]},
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "status": "fail",
                "message": "Invalid username or password.",
            },
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
