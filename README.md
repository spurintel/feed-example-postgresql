# feed-example-postgresql


## Overview

This project is designed to download Spur data feeds and ingest them into a PostgreSQL database.

This uses SQLAlchemy for the database modeling.  This ORM makes it easier to use the data programmatically
with Python or build integrations or applications on top.

The data is organized into table partitions by data type and day, so data may be easily aged off.
Daily partitions match the cadance of most data feeds, so running the ingest once per day will keep
everything up to date.

This also uses psycopg to bulk load (PostgreSQL COPY) the JSON data files in a performant way.


## Docker example

Not scaled for production use.

usage:
```
docker compose up -d
```