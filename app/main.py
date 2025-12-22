from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
import time

from app.config import settings
from app.core.database import create_db_and_tables
from app.api.routes import api_router


from app.core.logging import traffic_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    traffic_logger.info("Application Startup: Database connected.")
    yield
    traffic_logger.info("Application Shutdown.")

app = FastAPI(title="Applify", lifespan=lifespan)

@app.middleware("http")
async def log_traffic(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log details: Method, Path, Status Code, Duration
    log_message = (
        f"Method: {request.method} | "
        f"Path: {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.4f}s"
    )
    traffic_logger.info(log_message)
    
    return response

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")
app.mount("/static/resumes", StaticFiles(directory=settings.UPLOAD_DIR), name="resumes")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)