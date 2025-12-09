import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db, Base, engine
from src.routers.users import router as user_router
from src.routers.auth import router as auth_router


app = FastAPI(title="User Management API")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(user_router)
app.include_router(auth_router)


@app.get("/")
async def home(db: AsyncSession = Depends(get_db)):
    return {"message": "Database is connected and async!"}
