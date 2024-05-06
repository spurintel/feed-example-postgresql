import psycopg
import gzip
from psycopg import sql
from datetime import datetime, timedelta

# Database connection parameters
dbname = "postgres"
user = "postgres"
password = "spur_example_CHANGEME"
host = "localhost"

# TODO: Fetch files
# curl -o anonymous-residential.json.gz -L -H "Token: $API_TOKEN" "https://feeds.spur.us/v2/anonymous-residential/latest.json.gz"
# curl -o anonymous.json.gz -L -H "Token: $API_TOKEN" "https://feeds.spur.us/v2/anonymous/latest.json.gz"
# curl -o anonymous-ipv6.json.gz -L -H "Token: $API_TOKEN" "https://feeds.spur.us/v2/anonymous-ipv6/latest.json.gz"
# curl -o anonymous-residential-ipv6.json.gz -L -H "Token: $API_TOKEN" "https://feeds.spur.us/v2/anonymous-residential-ipv6/latest.json.gz"

# TODO: Get x-feed-generation-date from header
feed_date="20240503"

# PostgreSQL partition by dates
# Each range's bounds are inclusive at the lower end and exclusive at the upper end.
# So end date will be tomorrow, BUT tomorrow's data will not be in this partition
feed_date_obj = datetime.strptime(feed_date, "%Y%m%d").date()
feed_date_end_obj = feed_date_obj + timedelta(days=1)
feed_date_end = feed_date_end_obj.strftime("%Y%m%d")

# Connect to your postgres DB
conn = psycopg.connect(dbname=dbname, user=user, password=password, host=host)

# Open a cursor to perform database operations
cur = conn.cursor()

# Create data table
create_anon_table = sql.SQL("""
DROP TABLE IF EXISTS spur_anonymous;
CREATE TABLE IF NOT EXISTS spur_anonymous (
    ip inet NOT NULL,
    organization text,
    feed_date DATE NOT NULL DEFAULT CURRENT_DATE
) PARTITION BY RANGE (feed_date);
""")
cur.execute(create_anon_table)

# Create partition table
create_part_table = sql.SQL(f"""
DROP TABLE IF EXISTS spur_anonymous_{feed_date};
CREATE TABLE IF NOT EXISTS spur_anonymous_{feed_date} PARTITION OF spur_anonymous
FOR VALUES FROM ('{feed_date}') TO ('{feed_date_end}');
""")
cur.execute(create_part_table)

# create temp table
# can put this in a fast tablespace if you have one
create_temp_table = sql.SQL("""
CREATE TEMP TABLE temp_spur (data JSONB)
ON COMMIT DROP
""")
cur.execute(create_temp_table)

# Load data into the temporary table
with gzip.open("anonymous-residential.json.gz", 'rt') as datafile:
    # This is JSON not CSV we are importing, but this preserves escaped quotes in JSON
    # without expensive ingle line imports or string processing
    with cur.copy("COPY temp_spur (data) FROM STDIN CSV QUOTE e'\x01' DELIMITER e'\x02'") as copy:
        while data := datafile.read(32000):
            copy.write(data)

# Load the data from the temp table into the appropriate partition
process_temp_table = sql.SQL(f"""
INSERT INTO spur_anonymous
SELECT (data->>'ip')::inet as ip, data->>'organization' as organization, '{feed_date}' as feed_date
FROM temp_spur;
""")
cur.execute(process_temp_table)
conn.commit()

# Close the cursor and connection to the server
cur.close()
conn.close()

