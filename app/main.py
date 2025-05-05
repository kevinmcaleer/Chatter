from fastapi import FastAPI
from .database import create_db_and_tables
from .auth import router as auth_router
from .likes_comments import router as lc_router
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
app.include_router(lc_router, prefix="/interact")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(auth_router, prefix="/auth")
