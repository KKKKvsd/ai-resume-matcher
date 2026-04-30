import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware .cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from app.core.database import Base, engine

import app.models.user
import app.models.resume
import app.models.job
import app.models.match_result

from app.api.user import router as user_router
from app.api.job import router as job_router
from app.api.resume import router as resume_router
from app.api.match import router as match_router
from app.utils.response import error_response
from app.core.logger import logger

app = FastAPI(title="AI Resume Matcher")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    frontend_origin,
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    print("registered tables before create:", list(Base.metadata.tables.keys()), flush=True)
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            result = conn.execute(text("SELECT current_database()"))
        elif engine.dialect.name == "mysql":
            result = conn.execute(text("SELECT DATABASE()"))
        else:
            result = None
        
        if result is not None:
            logger.info(f"Current database: {result.scalar()}")
        else:
            logger.info(f"Current database dialect: {engine.dialect.name}")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code, 
        content=error_response(message=exc.detail, code=exc.status_code*100),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422, 
        content=error_response(
            message="request validation error", 
            code=42200,
            data=exc.errors(),
        ),
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=500, 
        content=error_response(
            message="internal server error", 
            code=5000,
        ),
    )

app.include_router(user_router)
app.include_router(job_router)
app.include_router(resume_router)
app.include_router(match_router)

@app.get("/ping")
def ping():
    return {"message": "pong"}