
from sqlalchemy import create_engine, Column, Integer, Date, Text, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import INET, TIMESTAMP
from sqlalchemy.sql import func
from datetime import datetime, timedelta

FEED_TYPES = ['anonymous', "anonymous_residential", "anonymous_ipv6", "anonymous_residential_ipv6"]

Base = declarative_base()

engine = create_engine('postgresql+psycopg://postgres:spur_example_CHANGEME@localhost/postgres', echo=True)

# Define the parent table with a compound primary key
class SpurFeeds(Base):
    __tablename__ = 'spur_feed'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(INET, primary_key=True)
    feed_type = Column(Text, nullable=False, primary_key=True)
    feed_date = Column(Date, nullable=False, primary_key=True, default=func.current_date())
    organization = Column(Text)
    load_time = Column(TIMESTAMP, default=func.now().op('AT TIME ZONE')('UTC'))
    __table_args__ = {'postgresql_partition_by': 'LIST (feed_type)'}

def init_db():
    with engine.begin() as conn:
        # Make the main table
        SpurFeeds.__table__.create(bind=conn, checkfirst=True)

        # Make partitions for each data type
        for feed_type in FEED_TYPES:
            partition = text(f"""
                DROP TABLE IF EXISTS spur_feed_{feed_type};
                CREATE TABLE IF NOT EXISTS spur_feed_{feed_type}
                PARTITION OF spur_feed
                FOR VALUES IN ('{feed_type}')
                PARTITION BY RANGE (feed_date)
                """)
            conn.execute(partition)

def create_date_partition(feed_type, feed_date):

    # PostgreSQL partition by dates
    # Each range's bounds are inclusive at the lower end and exclusive at the upper end.
    # So end date will be tomorrow, BUT tomorrow's data will not be in this partition
    # This conversion also serves as input sanitization
    feed_date_obj = datetime.strptime(feed_date, "%Y%m%d").date()
    feed_date_end_obj = feed_date_obj + timedelta(days=1)
    feed_date_end = feed_date_end_obj.strftime("%Y%m%d")

    if feed_type in FEED_TYPES:
        partition = text(f"""
        CREATE TABLE IF NOT EXISTS spur_feed_{feed_type}_{feed_date}
        PARTITION OF spur_feed_{feed_type}
        FOR VALUES FROM ('{feed_date}') TO ('{feed_date_end}')
        """)

        with engine.begin() as conn:
            conn.execute(partition)
    else:
        print(f"Feed type {feed_type} must be one of {FEED_TYPES}")