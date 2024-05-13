from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Union

from fastapi import FastAPI
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey, Date, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import INET, JSONB, ARRAY
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress
from datetime import date, datetime, time, timedelta
from feeds_db import SpurFeed, AutonomousSystem

# # Database URL (Adjust according to your settings)
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"

# # Database engine
# engine = create_engine(SQLALCHEMY_DATABASE_URL)
engine = create_engine('postgresql+psycopg://postgres:spur_example_CHANGEME@localhost/postgres', echo=True)

# Session Local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app initialization
app = FastAPI()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# class SpurFeedBase(BaseModel):
#     ip: str
#     as_number: int
#     client: dict
#     infrastructure: str
#     organization: str
#     location: dict
#     services: list
#     tunnels: dict
#     risks: list
#     feed_type: str
#     feed_date: date
#     load_time: datetime

# class SpurFeedCreate(SpurFeedBase):
#     pass

# class SpurFeed(SpurFeedBase):
#     id: int
#     class Config:
#         orm_mode = True

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}

class SpurFeedIP(BaseModel):
    ip: str

    class Config:
        orm_mode = True

@app.get("/spur_feeds/ip/{ip}", response_model=list[SpurFeedIP])
def read_spur_feed_by_ip(ip: IPvAnyAddress, db: Session = Depends(get_db)):
    results = db.query(SpurFeed).filter(SpurFeed.ip.op('<<')(ip)).all()
    if not results:
        raise HTTPException(status_code=404, detail="IP not found")
    return results

# db.session.query(TableIpAddress).filter(TableIpAddress.ipaddress.op('<<')(ip)).all()

# @app.get("/devices/")
# def read_device_by_ip(ip: IPAddress, db: Session = Depends(get_db)):
#     device = db.query(Device).filter(Device.ip_address == str(ip.ip_address)).first()
#     if device is None:
#         raise HTTPException(status_code=404, detail="Device not found")
#     return {"id": device.id, "ip_address": device.ip_address}