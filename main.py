from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# from fastapi.middleware.sessions import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware

import sqlite3

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="SUPER_SECRET_SESSION_KEY")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create table if it doesn't exist
conn = sqlite3.connect("users.db")
conn.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL)''')
conn.close()

# ------------------ LOGIN & REGISTRATION -------------------

@app.get("/", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cur.fetchone()
    conn.close()
    if user:
        request.session["username"] = username
        if username == "admin":
            return RedirectResponse("/admin", status_code=303)
        return RedirectResponse("/user", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": ""})

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return RedirectResponse("/", status_code=303)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/user", response_class=HTMLResponse)
async def user_home(request: Request):
    username = request.session.get("username")
    if not username or username == "admin":
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(f"<h2>Welcome to your page, {username}!</h2><br><a href='/logout'>Logout</a>")

# ------------------ ADMIN -------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("username") != "admin":
        return RedirectResponse("/", status_code=303)
    users = get_all_users()
    return templates.TemplateResponse("admin.html", {"request": request, "users": users, "error": ""})

@app.post("/admin/add", response_class=HTMLResponse)
async def admin_add_user(request: Request, username: str = Form(...), password: str = Form(...)):
    if request.session.get("username") != "admin":
        return RedirectResponse("/", status_code=303)
    try:
        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("admin.html", {"request": request, "users": get_all_users(), "error": "Username already exists"})
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/delete/{user_id}", response_class=HTMLResponse)
async def admin_delete_user(request: Request, user_id: int):
    if request.session.get("username") != "admin":
        return RedirectResponse("/", status_code=303)
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

def get_all_users():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users")
    users = cur.fetchall()
    conn.close()
    return users