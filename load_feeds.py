import os
import psycopg
import gzip
from psycopg import sql
import tempfile
import requests
from feeds_db import SpurFeeds, init_db, create_date_partition, FEED_TYPES

# Database connection parameters
dbname = "postgres"
user = "postgres"
password = "spur_example_CHANGEME"
host = "localhost"
SPUR_API_TOKEN = os.getenv('API_TOKEN', None)

# Connect to your postgres DB
conn = psycopg.connect(dbname=dbname, user=user, password=password, host=host)

# Open a cursor to perform database operations
cur = conn.cursor()

def download_feed(feed_type):
    headers = {
        'Token': f'{SPUR_API_TOKEN}'
    }
    # We expect to get a redirect URL and the feed generation date from the header
    url = f'https://feeds.spur.us/v2/{feed_type}/latest.json.gz'
    response = requests.get(url, headers=headers, allow_redirects=False)
    if response.status_code == 302:
        feed_date = response.headers.get('x-feed-generation-date', None)
        url_redirect = response.headers.get('Location', None)
        jar = response.cookies
    else:
        print(f"Failed to retrieve redirect with status code: {response.status_code}")
        return None

    # Then we expect to download the actual feed file from the redirect
    response = requests.get(url_redirect, headers=headers, cookies=jar, stream=True)

    if response.status_code == 200:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
            # Write the contents of the response to the temp file
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file.flush()
            # Print the path to the temporary file
            print(f"{feed_type} downloaded successfully to {temp_file.name}")
            return (temp_file.name, feed_date)
    else:
        print(f"Failed to retrieve file with status code: {response.status_code}")
        return None


def load_feed(feed_type, feed_file, feed_date):

    # create temp table
    # can put this in a fast tablespace if you have one
    create_temp_table = sql.SQL("""
    CREATE TEMPORARY TABLE temp_spur (data JSONB)
    ON COMMIT DROP
    """)
    cur.execute(create_temp_table)

    # Load data into the temporary table
    with gzip.open(feed_file, 'rt') as datafile:
        # This is JSON not CSV we are importing, but this preserves escaped quotes in JSON
        # without expensive ingle line imports or string processing
        with cur.copy("COPY temp_spur (data) FROM STDIN CSV QUOTE e'\x01' DELIMITER e'\x02'") as copy:
            while data := datafile.read(32000):
                copy.write(data)
 
    # Load the data from the temp table into the appropriate partition
    # Putting IPv4 and IPv6 is the same ip field, because PostgreSQL inet types can handle both.
    if feed_type.endswith('ipv6'):
        ip_transform = "(data->>'network')::cidr"
    else:
        ip_transform = "(data->>'ip')::inet"
    process_temp_table = sql.SQL(f"""
        INSERT INTO spur_feed (ip, feed_type, feed_date, organization, load_time)
        SELECT {ip_transform} as ip, 
            '{feed_type}' as feed_type,
            '{feed_date}'::date as feed_date,
            data->>'organization' as organization,
            CURRENT_TIMESTAMP AT TIME ZONE 'UTC' as load_time
        FROM temp_spur;
        """)
    cur.execute(process_temp_table)
    conn.commit()


if __name__ == '__main__':

    # # Connect to your postgres DB
    # conn = psycopg.connect(dbname=dbname, user=user, password=password, host=host)

    # # Open a cursor to perform database operations
    # cur = conn.cursor()

    init_db()
    for feed_type in ['anonymous','anonymous-ipv6']:
        # download feed to a temp file
        (feed_file, feed_date) = download_feed(feed_type)
        # This converts the feed names from hyphenated to underscored
        # It isn't ideal, but Postgres doesn't like hyphens in table and column names
        create_date_partition(feed_type.replace('-','_'), feed_date)
        load_feed(feed_type.replace('-','_'), feed_file, feed_date)

    #     # delete feed temp file
    #     os.remove(feed_file)

    # Close the cursor and connection to the server
    # cur.close()
    # conn.close()

