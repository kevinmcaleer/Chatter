from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastui import FastUI, AnyComponent, prebuilt_html, components as c
from fastui.components import PageTitle, Table as DataTable
from fastui.models import TableColumn

import sqlite3

app = FastAPI()
app.mount("/ui", FastUI())

DB_PATH = "users.db"

@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/ui/users")

@app.get("/ui/users", response_model=c.Page)
def list_users_ui():
    # Connect to the database and fetch users
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users")
        users = cursor.fetchall()

    return Page(
        title="All Users",
        components=[
            PageTitle(text="Registered Users"),
            DataTable(
                data=[{"id": user[0], "username": user[1]} for user in users],
                columns=[
                    TableColumn(label="ID", key="id"),
                    TableColumn(label="Username", key="username")
                ]
            )
        ]
    )
