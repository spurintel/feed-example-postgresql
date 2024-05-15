from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey, Date, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import INET, JSONB, ARRAY
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress, IPvAnyNetwork
from datetime import date, datetime, time, timedelta
from typing import Dict, Any
from feeds_db import SpurFeed
from ipaddress import IPv6Address
import os

SQLALCHEMY_URL = os.getenv('SQLALCHEMY_URL', None)
if not SQLALCHEMY_URL:
    raise ValueError("SQLALCHEMY_URL environment variable is not set")

# Database engine
engine = create_engine(SQLALCHEMY_URL, echo=True)

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
    print(type(ip))

    # If IPv4 or IPv6 address, query (=) anonymous and anonymous-residential IPS
    results = db.query(SpurFeed).filter(
        SpurFeed.feed_type.in_(['anonymous', 'anonymous-residential'])).filter(
            SpurFeed.ip.op('=')(ip)).order_by(
                SpurFeed.feed_date.desc()).first()
    # If no exact (=) matches and IPv6, query (>>) anonymous-ipv6 and anonymous-residential-ipv6 NETWORKS
    if not results and isinstance(ip, IPv6Address):
        results = db.query(SpurFeed).filter(
             SpurFeed.feed_type.in_(['anonymous-ipv6', 'anonymous-residential-ipv6'])).filter(
                 SpurFeed.ip.op('>>')(ip)).order_by(SpurFeed.feed_date.desc()).first()
    if not results:
        raise HTTPException(status_code=404, detail="IP not found")
    return results.context