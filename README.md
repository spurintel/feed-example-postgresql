# feed-example-postgresql


## Overview

This project is designed to download Spur data feeds and ingest them into a PostgreSQL database. 
It also provides a local version of the Spur Context API backed by this database.

The data is organized into table partitions by data type and day, so data may be easily aged off
by simply dropping older partitions.
Daily partitions match the cadence of most data feeds, so running the ingest once per day will keep
everything up to date.

## Requirements

Requires a recent version of Docker, and approximately 35GB (and growing) of free disk space per day of feeds you wish to store.

Like any database application, faster disks and more RAM available for caching will largely determine the performance.

## Column definitions

Detailed information on Spur feeds can be found at https://docs.spur.us/feeds

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

Assumes you have a recent version of Docker and are comfortable using the command line. ([Get Docker](https://docs.docker.com/get-docker/))

1) Build the Docker API image
   ```sh
   docker compose build
   ```

2) Launch the PostgreSQL container and API:
   ```sh
   docker compose up -d
   ```

3) At his point the following should be running: 
   - PostgreSQL on `localhost:5432`
   - The Context API on http://localhost:8000/v2/context/ {ip}
   - Documentation and an API test GUI on http://localhost:8000/docs

### Load the data

1) Make your Spur token available as an environment variable:
   ```sh
   export SPUR_API_TOKEN=YOUR_FEED_ACCESS_TOKEN
   ```
   Add this to your shell run control file if you will use this regularly.  (~/.bashrc, ~/.zshrc, etc.) 

2) Optionally limit the feeds which will be processed by setting the `FEED_TYPES` variable in the provided `db.env` file.  
   By default it will attempt to get all supported types.  e.g. `FEED_TYPES=["anonymous-ipv6"]`

3) Load the data
   ```sh
   docker compose run --rm load-feeds
   ```
   This downloads the feeds to a temporary file and performs a bulk load (PostgreSQL COPY) of the JSON data files.  This will take some time, 
   especially for the very large `anonymous-residential` feed.  Approximately 20 minutes on a MacBook Pro M1.

4) Visit http://localhost:8000/docs and click "Try it out"  
   Enter an IP address and click Execute.


### Prune the data

This docker example will be functional on modern desktop hardware, but has not been tuned for production.  
Performance will vary greatly depending on the hardware you use, Docker settings, and how many days you keep online.  

A script is provided to drop tables with feeds that are older than x `--days` old.  Older data is less likely to be accurate 
and will slow down queries, so keeping more than a few days online is counterproductive unless you have a historical use case.  

   Parameters:  
   `--days` is required  
   `--force` is an optional parameter, but it will not prompt for confirmation and cannot be undone  

   - Example:  
      ```sh
      docker compose run --rm prune-feeds --days 2
      ```

### Extras

Apart from the API, you can access the PostgreSQL directly if you wish to perform advanced queries or integrate with something else.

The docker-compose file also contains definitions for adminer and pgadmin4, but they are not started by default.  
Adminer is a lightweight but ugly SQL interface, and pgadmin4 is a full featured but complex SQL interface.

#### Start Pgadmin4  
   ```sh
   docker compose up pgadmin -d
   ```
   - Log in: 
   http://localhost:8081/  
   Default user: example@spur.us  
   Default password: spur_example_CHANGEME  

#### Start Adminer
  
   ```sh
   docker compose up adminer -d
   ```
   - Log in: 
   http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public  
   Default password: spur_example_CHANGEME  

#### See the tables that have been created:
   - http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&select=spur

#### Example Queries

The `ip` column is a PostgreSQL INET type, which supports all kinds of network selections for addresses and subnets and netmasks in both ipv4 and ipv6.  
- [Complete list of network address functions and operators](https://www.postgresql.org/docs/current/functions-net.html)

The `context` column is a PostgreSQL JSONB type, which allow arbitrary JSON values and can easily be extended without database changes.  
- [Complete list of JSON functions and operators](https://www.postgresql.org/docs/current/functions-json.html)

Note that these particular IP addresses are examples and may or may not be in the data set when you load it.

- Query for a single IP:  
[select * FROM spur  
WHERE ip = '196.242.10.22'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20ip%20%3D%20%27196.242.10.22%27%0ALIMIT%20100%0A)

- Query for a subnet:  
[select * FROM spur  
WHERE ip << '196.242.0.0/24'  
LIMIT 100](http://localhost:8080/?pgsql=db&username=postgres&db=postgres&ns=public&sql=select%20*%20FROM%20spur%20%0AWHERE%20ip%20%3C%3C%20%27196.242.10.0%2F24%27%0ALIMIT%20100%0A)

### Misc. Notes

Since this is normally a read-only feed, data can be re-ingested.  Even so, it is occasionally useful to backup/restore older data, and this is one way.

- Backup
   ```
   pg_dump -h localhost -p 5432 -U postgres -d postgres -t "spur*" > spur_anonymous_backup.sql
   ```

- Restore
   ```
   psql -h localhost -p 5432 -U postgres -d postgres -f spur_anonymous_backup.sql
   ```