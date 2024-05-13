from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey, Date, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import INET, JSONB, ARRAY
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel, Json
from pydantic.networks import IPvAnyAddress
from datetime import date, datetime, time, timedelta
from typing import Dict, Any
from feeds_db import SpurFeed
from ipaddress import IPv4Address, IPv6Address


# # Database engine
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

class SpurFeedIP(BaseModel):
    ip: IPvAnyAddress
    context: Dict[str, Any]
    feed_date: datetime

    class Config:
        orm_mode = True

@app.get("/v2/context/{ip}", response_model=Dict[str, Any])
async def read_spur_feed_by_ip(ip: IPvAnyAddress, db: Session = Depends(get_db)):
    results = db.query(SpurFeed).filter(SpurFeed.ip.op('=')(ip)).order_by(SpurFeed.feed_date.desc()).first()
    if not results:
        raise HTTPException(status_code=404, detail="IP not found")
    return results.context