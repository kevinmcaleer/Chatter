from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .database import create_db_and_tables
from .auth import router as auth_router
from .likes_comments import router as lc_router
from .accounts import router as accounts_router
from dotenv import load_dotenv
import os
load_dotenv()

# Initialize rate limiter (disabled in testing)
TESTING = os.getenv("TESTING", "false").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=not TESTING)

app = FastAPI()

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
# In production, set ALLOWED_ORIGINS environment variable to your domain(s)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(lc_router, prefix="/interact")
app.include_router(auth_router, prefix="/auth")
app.include_router(accounts_router, prefix="/accounts")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "chatter"}
