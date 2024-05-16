#!/bin/env python

import os
import psycopg
import gzip
from psycopg import sql
import tempfile
import requests
from feeds_db import init_db, create_date_partition, FEED_TYPES
from datetime import datetime, timedelta
import argparse

# Database connection parameters
PSYCOPG_URL = os.getenv('PSYCOPG_URL', None)
if not PSYCOPG_URL:
    raise ValueError("PSYCOPG_URL environment variable is not set")

# Connect to your postgres DB
conn = psycopg.connect(PSYCOPG_URL)

# Open a cursor to perform database operations
cur = conn.cursor()

def list_tables_to_prune(days):
    # return a list of outdated tables

    # Execute a query to retrieve the list of tables
    cur.execute(rf"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        AND table_name ~ '^spur_anonymous.*[0-9]{{8}}$'
        AND (current_date - INTERVAL '{days} days') > to_date(substring(table_name from '(\d{{8}})$'), 'YYYYMMDD');
    """)

    # Fetch the results
    tables = cur.fetchall()

    # Convert the results to a Python list
    table_list = [table[0] for table in tables]
    return table_list

def prompt_for_confirmation(prompt="Do you want to continue? (y/n): "):
    while True:
        response = input(prompt).lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please respond with 'y' or 'n'.")

def drop_table(tablename, force):

    if force or prompt_for_confirmation(f"Drop table {tablename}? This cannot be undone. (y/n)"):
        try:
            # Execute the SQL command to drop the table
            cur.execute(f"DROP TABLE IF EXISTS {tablename};")
            # Commit the transaction
            conn.commit()
            print(f"Table '{tablename}' dropped successfully.")

        except Exception as e:
            print(f"Error: {e}")
            # Rollback the transaction in case of error
            conn.rollback()
    else:
        print("Cancelled.")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Prune old Spur feeds from the database.")
    parser.add_argument('--days', type=int, required=True, help='Number of days to delete')
    parser.add_argument('--force', type=bool, nargs='?', const=True, default=False, help='An integer parameter')
    args = parser.parse_args()

    tables = list_tables_to_prune(args.days)
    print(f"Spur feed tables more than {args.days} day(s) old: {len(tables)}")
    for table in tables:
        drop_table(table, args.force)

    # Close the cursor and connection to the server
    cur.close()
    conn.close()

