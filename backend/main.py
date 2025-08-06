# =================================================================
# SECTION 1: IMPORTS
# All 'import' statements go here first.
# =================================================================
import os
import json
import logging
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from passlib.context import CryptContext
from jose import JWTError, jwt

# Your project's specific modules
from config import WHITELIST, BLACKLIST
from optimized_scraper import OptimizedUniversalScraper

# =================================================================
# SECTION 2: CONFIGURATION AND GLOBAL SETUP
# All global variables and setup code go here.
# =================================================================
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
DATABASE_URL = "local_database.db"
SECRET_KEY = "a_very_secret_key_for_mvp"  # In production, load this from a .env file
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =================================================================
# SECTION 3: PYDANTIC DATA MODELS
# Define all your data validation models here.
# =================================================================
class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ScrapeRequest(BaseModel):
    url: HttpUrl

class ScrapeResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

# =================================================================
# SECTION 4: HELPER FUNCTIONS & CLASSES
# Authentication helpers, RateLimiter, etc.
# =================================================================
class RateLimiter:
    def __init__(self, max_requests: int, db_connection, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.db = db_connection

    def is_allowed(self, user_id: str) -> bool:
        cursor = self.db.cursor()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)

        # Delete old log entries outside the window for the current user
        cursor.execute(
            "DELETE FROM rate_limit_log WHERE user_id = ? AND timestamp < ?",
            (user_id, window_start)
        )
        
        # Count recent requests for the user
        cursor.execute(
            "SELECT COUNT(*) FROM rate_limit_log WHERE user_id = ?",
            (user_id,)
        )
        request_count = cursor.fetchone()[0]

        if request_count >= self.max_requests:
            self.db.commit()
            return False
        
        # Log the current request
        cursor.execute(
            "INSERT INTO rate_limit_log (user_id, timestamp) VALUES (?, ?)",
            (user_id, now)
        )
        self.db.commit()
        return True

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, token: str = Depends(jwt.decode)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    cursor = request.app.state.db.cursor()
    user = cursor.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    
    if user is None:
        raise credentials_exception
    return user

# =================================================================
# SECTION 5: DATABASE LIFESPAN MANAGER
# This function manages resources during the app's life.
# =================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup logic
    logging.info("Starting Universal Scraper API...")
    app.state.db = sqlite3.connect(DATABASE_URL)
    app.state.db.row_factory = sqlite3.Row  # Allows accessing columns by name
    logging.info("Database connection established.")
    yield
    # Shutdown logic
    logging.info("Shutting down Universal Scraper API...")
    app.state.db.close()
    logging.info("Database connection closed.")

# =================================================================
# SECTION 6: INITIALIZE THE FASTAPI APP
# =================================================================
app = FastAPI(
    title="Universal Web Scraper API",
    description="High-performance web scraping API with SSE streaming",
    version="1.0.0",
    lifespan=lifespan
)

# =================================================================
# SECTION 7: MIDDLEWARE
# =================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# =================================================================
# SECTION 8: SSE EVENT GENERATOR
# =================================================================
async def generate_sse_events(url: str, user_id: Optional[str] = None):
    """Generate Server-Sent Events for the scraping workflow."""
    try:
        async with OptimizedUniversalScraper() as scraper:
            async for update in scraper.run(str(url)):
                # Convert WorkflowOutput to SSE format
                event_data = {
                    "current_stage": update.current_stage,
                    "total_stages": update.total_stages,
                    "status": update.status,
                    "stage": update.stage,
                    "message": update.message,
                    "performance_metrics": update.performance_metrics
                }
                
                if update.data:
                    event_data["data"] = update.data
                
                if update.error:
                    event_data["error"] = update.error
                
                # Format as SSE event
                yield f"event: {update.status}\n"
                yield f"data: {json.dumps(event_data)}\n\n"
                
                # If complete or error, end the stream
                if update.status in ["complete", "error"]:
                    break
                    
    except Exception as e:
        logger.exception(f"Error in SSE stream for {url}: {e}")
        error_event = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "current_stage": 0,
            "total_stages": 6
        }
        yield f"event: error\n"
        yield f"data: {json.dumps(error_event)}\n\n"

# =================================================================
# SECTION 9: API ENDPOINTS / ROUTES
# =================================================================
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Universal Web Scraper API"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

@app.post("/register", status_code=201)
async def register_user(user: UserCreate, request: Request):
    """Register a new user."""
    db = request.app.state.db
    cursor = db.cursor()
    
    # Check if user already exists
    existing_user = cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,)).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
        (user.email, hashed_password)
    )
    db.commit()
    return {"message": "User created successfully"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: UserCreate, request: Request):
    """Login and get access token."""
    db = request.app.state.db
    cursor = db.cursor()
    user = cursor.execute("SELECT * FROM users WHERE email = ?", (form_data.email,)).fetchone()
    
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user['id'])}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/scrape-stream")
async def scrape_stream(
    request: Request,
    scrape_req: ScrapeRequest,
    current_user: sqlite3.Row = Depends(get_current_user)
):
    """Stream scraping progress via Server-Sent Events."""
    # Initialize RateLimiter with the db connection from the request state
    rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE, request.app.state.db)

    # Rate limiting
    user_id_str = str(current_user['id'])
    if not rate_limiter.is_allowed(user_id_str):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_PER_MINUTE} requests per minute."
        )

    # Log the request
    logger.info(f"Scraping request for {scrape_req.url} from user {user_id_str}")

    # The generator needs to be adapted to save data
    async def sse_and_save_generator():
        final_data = None
        async for update in generate_sse_events(str(scrape_req.url), user_id_str):
            yield update
            # Snag the final data packet to save it
            if update.status == 'complete' and update.data:
                final_data = update.data

        # After the stream is finished, save to DB if it was successful
        if final_data and current_user:
            db = request.app.state.db
            cursor = db.cursor()
            article = final_data
            metadata = article.get('metadata', {})
            cursor.execute("""
                INSERT INTO scraped_articles (user_id, original_url, title, author, publication_date, word_count, content_markdown)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user['id'],
                article.get('url'),
                article.get('title'),
                metadata.get('author'),
                metadata.get('publication_date_utc'),
                metadata.get('word_count'),
                article.get('content', {}).get('markdown')
            ))
            db.commit()
            logger.info(f"Saved article '{article.get('title')}' to history for user {current_user['id']}.")

    # Return SSE stream
    return StreamingResponse(
        sse_and_save_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/v1/requests")
async def request_site_support(
    request: Request,
    current_user: sqlite3.Row = Depends(get_current_user)
):
    """Log user requests for site support."""
    db = request.app.state.db
    cursor = db.cursor()

    try:
        body = await request.json()
        requested_domain = body.get("requested_domain")

        if not requested_domain:
            raise HTTPException(status_code=400, detail="requested_domain is required")

        # Log the request to the database
        cursor.execute(
            "INSERT INTO site_requests (user_id, requested_domain) VALUES (?, ?)",
            (current_user['id'], requested_domain)
        )
        db.commit()
        logger.info(f"Site support requested for {requested_domain} by user {current_user['id']}")

        return {"status": "success", "message": "Request logged successfully"}

    except Exception as e:
        logger.exception(f"Error logging site support request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/whitelist")
async def get_whitelist():
    """Get the current whitelist of supported sites."""
    return {
        "whitelist": WHITELIST,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

@app.get("/v1/blacklist")
async def get_blacklist():
    """Get the current blacklist of unsupported sites."""
    return {
        "blacklist": BLACKLIST,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

# =================================================================
# SECTION 10: APPLICATION ENTRY POINT
# =================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 