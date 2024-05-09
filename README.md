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

```
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
```

## Docker example

Requires a recent version of Docker on Linux or MacOS.

Launch a PostgreSQL container:
```sh
docker compose up -d
```

This starts a copy of PostgreSQL running on `localhost:5432`  It also starts a copy of Adminer on http://localhost:8080 which is an ugly but simple interface into the database.

These are only listening on the local interface for security reasons.  Do not change it unless you know what you are doing.  The default password is "spur_example_CHANGEME".  You can change it before launch in the `docker-compose.yml` file.

This also starts pgadmin4 on http://localhost:80.  It is a powerful tool, but complex beyond the scope of this example.  If you wish to use it, default user is "example@spur.us" password "spur_example_CHANGEME".  Click "add a new server" and set the connection parameters host: db, username: postgres, and password: spur_example_CHANGEME.

### Load the data

The data is downloaded and then loaded into the database using a Python script `load_feeds.py`.  Requires a recent version of Python 3.

1) Make your Spur token available as an environment variable:
```sh
export SPUR_API_TOKEN=YOUR_FEED_ACCESS_TOKEN
```

2) Change your DB password in `load_feeds.py` and `feeds_db.py` if you have changed it from the default.

3) Install Python dependencies
```sh
pip3 install -r requirements.txt
```

4) Optionally limit the feeds which will be processed by uncommenting and editing the `FEED_TYPES` list in `load_feeds.py`.  By default it will attempt to get all supported types.  e.g. `FEED_TYPES = ['anonymous-ipv6']`

5) Load the data
```sh
python load_feeds.py
```

### View the data

#### Log in:
http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public

#### See the tables that have been created:
http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&select=spur

#### Example Queries

The `ip` column is a PostgreSQL INET type, which supports all kinds of network selections for addresses and subnets and netmasks in both ipv4 and ipv6.  
[Complete list of network address functions and operators](https://www.postgresql.org/docs/current/functions-net.html)

The `client`, `location`, and `tunnels` fields are PostgreSQL JSONB types, which allow arbitrary JSON values and can easily be extended without database changes.  
[Complete list of JSON functions and operators](https://www.postgresql.org/docs/current/functions-json.html)

Note that these particular IP addresses are examples and may or may not be in the data set when you load it.

Query for a single IP:  
[select * FROM spur  
WHERE ip = '196.242.10.22'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20ip%20%3D%20%27196.242.10.22%27%0ALIMIT%20100%0A)

Query for a subnet:  
[select * FROM spur  
WHERE ip << '196.242.0.0/24'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20ip%20%3C%3C%20%27196.242.10.0%2F24%27%0ALIMIT%20100%0A)

Query for a specific country:  
[select * FROM spur  
WHERE location @> '{"country": "KP"}'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20location%20%40%3E%20%27%7B%22country%22%3A%20%22KP%22%7D%27%0ALIMIT%20100%0A)

Query for a specific country in a more human readable but less efficient way:  
[select * FROM spur  
WHERE location->>'country' = 'KP'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20location-%3E%3E%27country%27%20%3D%20%27KP%27%0ALIMIT%20100%0A%0A)

Query complex sets like only IPv6 iCloud proxies but not those in the Fastly ASN or within the US:  
[select * FROM spur  
WHERE family(ip) = 6  
AND tunnels @> '[{"operator": "ICLOUD_RELAY_PROXY"}]'  
AND NOT as_number = 54113  
AND NOT location @> '{"country": "US"}'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20family(ip)%20%3D%206%0AAND%20tunnels%20%40%3E%20%27%5B%7B%22operator%22%3A%20%22ICLOUD_RELAY_PROXY%22%7D%5D%27%0AAND%20NOT%20as_number%20%3D%2054113%0AAND%20NOT%20location%20%40%3E%20%27%7B%22country%22%3A%20%22US%22%7D%27%0ALIMIT%20100)

You can also extract values from the JSONB column and cast them to the appropriate type for comparison.
Query for entries that show a GEO_MISMATCH risk and a client count over 10:  
[SELECT ip, client  
FROM spur  
WHERE risks @> ARRAY['GEO_MISMATCH']  
AND (client->>'count')::int >10  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=SELECT%20ip%2C%20client%0AFROM%20spur%0AWHERE%20risks%20%40%3E%20ARRAY%5B%27GEO_MISMATCH%27%5D%0AAND%20(client-%3E%3E%27count%27)%3A%3Aint%20%3E10%0ALIMIT%20100)

Since the data is partitioned into tables by type and day, you can significantly increase query performance by limiting the tables you search.  Particularly if lots of data is loaded or if you have a slow DB server.  
Query from only a specific data type and day table:  
[SELECT * FROM "spur_anonymous_20240508"  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=SELECT%20*%0AFROM%20%22spur_anonymous_20240508%22%0ALIMIT%20100)

### Misc. Notes

Since this is normally a read-only feed, data can be reingested.  Even so, it is occasionally useful to backup/restore older data, and this is one way.

Backup
```
pg_dump -h localhost -p 5432 -U postgres -d postgres -t "spur*" > spur_anonymous_backup.sql
```

Restore
```
psql -h localhost -p 5432 -U postgres -d postgres -f spur_anonymous_backup.sql
```