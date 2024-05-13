
from sqlalchemy import create_engine, Column, Integer, Date, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.sql import func

Base = declarative_base()

engine = create_engine('postgresql+psycopg://postgres:spur_example_CHANGEME@localhost/postgres', echo=True)

# Define the parent table with a compound primary key and partition by feed_type
class SpurFeed(Base):
    __tablename__ = 'spur'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(INET, primary_key=True)
    context = Column(JSONB)
    feed_type = Column(Text, nullable=False, primary_key=True)
    feed_date = Column(Date, nullable=False, primary_key=True, default=func.current_date())
    __table_args__ = {'postgresql_partition_by': 'LIST (feed_type)'}
