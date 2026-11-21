from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .database import create_db_and_tables
from .auth import router as auth_router
from .likes_comments import router as lc_router
from .social import router as social_router
from .accounts import router as accounts_router
from .page_views import router as page_views_router
from .profile import router as profile_router
from .projects import router as projects_router
from .oauth import router as oauth_router, seed_clients
from .session_renewal import SlidingSessionMiddleware
from dotenv import load_dotenv
import os
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize rate limiter (disabled in testing)
TESTING = os.getenv("TESTING", "false").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=not TESTING)

app = FastAPI()

# Add custom exception handler for browser redirects
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    # Check if this exception has a redirect header (for browser auth failures)
    if hasattr(exc, 'headers') and exc.headers and "X-Redirect" in exc.headers:
        return RedirectResponse(url=exc.headers["X-Redirect"], status_code=303)
    # Otherwise, return the default JSON error
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),  # keeps WWW-Authenticate for app tokens (#80)
    )

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Renew login cookies on use so active users stay logged in.
# Added before CORS so CORS stays the outermost middleware.
app.add_middleware(SlidingSessionMiddleware)

# Configure CORS - MUST allow origin explicitly
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.kevsrobots.com",
        "https://kevsrobots.com",
        "http://localhost:3000",
        "http://localhost:4000",
        "http://localhost:8001",
        "http://0.0.0.0:4000",
        "http://local.kevsrobots.com:4000",
        "https://app.snakie.org",  # Snakie web: Sign in with kevsrobots token calls (#80)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.include_router(lc_router, prefix="/interact")
app.include_router(social_router, prefix="/interact")
app.include_router(auth_router)
app.include_router(accounts_router, prefix="/accounts")
app.include_router(page_views_router, prefix="/analytics")
app.include_router(profile_router)
app.include_router(projects_router, prefix="/api")
app.include_router(oauth_router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    try:
        from sqlmodel import Session
        from .database import engine
        with Session(engine) as session:
            seed_clients(session)
    except Exception:  # never stop the app starting over a seed
        logging.getLogger(__name__).exception("Couldn't seed the Sign in with kevsrobots clients")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "chatter"}
