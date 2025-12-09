import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,  # this is a car factory
    AsyncEngine,  # The car Bluprint
    AsyncSession,  # Driver
    async_sessionmaker,  # Driving school
)
from sqlalchemy.orm import DeclarativeBase  # like  a mother class for all the table

from typing import AsyncGenerator  # tell get_db() is slow use sync

from dotenv import load_dotenv  # getting the secret from .env

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine: AsyncEngine = create_async_engine(  # Build the car
    DATABASE_URL,  # Where the car Drive to , that location to database
    echo=False,  # If true it log the sql query for every action , set True in dev , silent mode (don't print every sql query)
    future=True,  # REQUIRED for SQLAlchemy 2.0 style (new and better)
    pool_size=20,  # Max simultaneous connection like " 20 Drivers ready to go"
    max_overflow=40,  # Allow bursting up to 60 , can hire 40 extra drivers when busy
    pool_pre_ping=True,  # Automatically fix dead Connections , car checks "Are you Alive" before driving
    pool_timeout=30,  # Wait max 30 seconds for a free driver
)

async_session = async_sessionmaker(  # Driving school
    bind=engine,  # School is connected to the car garage
    class_=AsyncSession,  # all Drivers are async (completely trined fast Drivers)
    expire_on_commit=False,  # Drivers remembers data after saving ,  after the drop the customers in location , the drive have details of the customers, if true the driver forget the data # ← Remember everything after commit
    autoflush=False,  # It prevent the data save it run time like  "driver write a name of the customer when he enter in to car , it customer suddenly cancel the rider the data is remain like is dropped " # ← Remember everything after commit
    autocommit=False,  # it say after the customer reach the location and exit the car only you need to store the data in note # ← I am the boss
)


class Base(DeclarativeBase):  # mother for all the table ,
    pass


async def get_db() -> (
    AsyncGenerator[AsyncSession, None]
):  # contact card  for Driving school
    async with async_session() as session:  # phone call for driving school and asking "hey driving school,give me one trained driver(session)"
        try:
            yield session  # Here is your driver "happy journey"
            await session.commit()  # if everything will done , Driver save the data
        except Exception:
            await session.rollback()  # If something Problem ,Driver clear the data
            raise
        finally:
            await session.close()  # No Matter what happen Driver ,go to home and rest
