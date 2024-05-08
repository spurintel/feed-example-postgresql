# feed-example-postgresql


## Overview

This project is designed to download Spur data feeds and ingest them into a PostgreSQL database.

This uses SQLAlchemy for the database modeling.  This ORM makes it easier to use the data programmatically
with Python or build integrations or applications on top.

The data is organized into table partitions by data type and day, so data may be easily aged off.
Daily partitions match the cadance of most data feeds, so running the ingest once per day will keep
everything up to date.

This also uses psycopg to bulk load (PostgreSQL COPY) the JSON data files in a performant way.

## Column definitions

ip                     The IP address queried
as                     Autonomous System Details
client.behaviors       Behaviors of clients on this IP
client.concentration   Location concentration of clients on this IP
client.count           Average number of clients observed per day
client.countries       Number of countries clients have come from
client.proxies         Call-back proxies running from devices on this IP
client.spread          The geographic spread of clients (km^2)
client.types           Types of client devices observed
infrastructure         The classification of infrastructure this IP is in
organization           The organization operating the IP address
location               Maxmind GeoLite2 location data
services               Protocols and services running on this IP (e.g. OpenVPN)
tunnels                VPN/Proxy/Anonymization details and operator information
risks                  Risks and threats from this IP address

## Docker example

usage:
```
docker compose up -d
```