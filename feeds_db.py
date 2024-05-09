
from sqlalchemy import create_engine, Column, Integer, Date, Text, text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import INET, TIMESTAMP, JSONB, ARRAY
from sqlalchemy.sql import func

FEED_TYPES = ['anonymous', "anonymous-residential", "anonymous-ipv6", "anonymous-residential-ipv6"]
# NOTE that some functions convert the feed names from hyphenated to underscored
# Not ideal, but Postgres doesn't like hyphens in table and column names
# You can use them, but then they have to be in quotes.  Which is differently non-ideal.

Base = declarative_base()

engine = create_engine('postgresql+psycopg://postgres:spur_example_CHANGEME@localhost/postgres', echo=True)

# Define the parent table with a compound primary key and partition by feed_type
class SpurFeed(Base):
    __tablename__ = 'spur'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(INET, primary_key=True)
    as_number = Column(Integer, ForeignKey('autonomous_systems.as_number'))
    client = Column(JSONB)
    infrastructure = Column(Text)
    organization = Column(Text)
    location = Column(JSONB)
    services = Column(ARRAY(Text))
    tunnels = Column(JSONB)
    risks = Column(ARRAY(Text))
    feed_type = Column(Text, nullable=False, primary_key=True)
    feed_date = Column(Date, nullable=False, primary_key=True, default=func.current_date())
    load_time = Column(TIMESTAMP, default=func.now().op('AT TIME ZONE')('UTC'))
    __table_args__ = {'postgresql_partition_by': 'LIST (feed_type)'}

    autonomous_system = relationship("AutonomousSystem", back_populates="spur")

# Define a table to store the repetitive AS information
# NOTE: "as" is a reserved word in PostgreSQL, so that field from the feed is renamed to "as_number"
class AutonomousSystem(Base):
    __tablename__ = 'autonomous_systems'
    as_number = Column(Integer, primary_key=True)
    organization_name = Column(Text, nullable=True, primary_key=False)

    spur_feed = relationship("SpurFeed", back_populates="autonomous_systems")

def init_db():
    with engine.begin() as conn:
        # Make the main table
        # SpurFeeds.__table__.create(bind=conn, checkfirst=True)
        # AutonomousSystem.__table__.create(bind=conn, checkfirst=True)
        Base.metadata.create_all(engine)

        # Make partitions for each data type
        for feed_type in FEED_TYPES:
            partition = text(f"""
                CREATE TABLE IF NOT EXISTS spur_{feed_type.replace('-','_')}
                PARTITION OF spur
                FOR VALUES IN ('{feed_type}')
                PARTITION BY RANGE (feed_date)
                """)
            conn.execute(partition)

def create_date_partition(feed_type, feed_date, feed_date_end):
    # Each range's bounds are inclusive at the lower end and exclusive at the upper end.
    # So end date will be tomorrow, BUT tomorrow's data will not be in this partition

    # This currently DROPS the table for today if it exists and recreates it.
    # This should only happen if the data is loaded multiple times in one day.
    # It should prevent duplicate records from being loaded in the same day.
    if feed_type in FEED_TYPES:
        partition = text(f"""
        DROP TABLE IF EXISTS spur_{feed_type.replace('-','_')}_{feed_date};
        CREATE TABLE spur_{feed_type.replace('-','_')}_{feed_date}
        PARTITION OF spur_{feed_type.replace('-','_')}
        FOR VALUES FROM ('{feed_date}') TO ('{feed_date_end}')
        """)

        with engine.begin() as conn:
            conn.execute(partition)
    else:
        print(f"Feed type {feed_type} must be one of {FEED_TYPES}")