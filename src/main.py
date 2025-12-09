from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db, Base, engine
from src.routers.users import router as user_router
from src.routers.auth import router as auth_router
from src.schemas.response import APIResponse


app = FastAPI(title="User Management API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=str(exc.detail),
            data=None
        ).dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=APIResponse(
            success=False,
            message="Validation Error",
            data={"errors": exc.errors()}
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Internal Server Error",
            data=str(exc)  # Probably shouldn't expose this in prod, but helpful for dev
        ).dict()
    )


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(user_router)
app.include_router(auth_router)


@app.get("/", response_model=APIResponse[dict])
async def home(db: AsyncSession = Depends(get_db)):
    return APIResponse(
        success=True,
        message="System Operational",
        data={"status": "Database is connected and async!"}
    )
