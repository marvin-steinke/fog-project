# Description: Check the existence and display the schema of the SQLite database file.

import sqlite3
import os
from sqlite3 import Error

def check_database(local_db_file):
    """Check the existence and display the schema of the SQLite database file.
    
    Args:
        local_db_file (str): Path to the local SQLite database file.
    """
    conn = None
    try:
        conn = sqlite3.connect(local_db_file)
        cursor = conn.cursor()
        
        # Check if the power_averages table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='power_averages'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("Database exists. Schema:")
            cursor.execute("PRAGMA table_info(power_averages)")
            schema_rows = cursor.fetchall()
            for row in schema_rows:
                print(row)
        else:
            print("Database does not exist or does not contain the expected table.")
        
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

# Usage example:
check_database('test.db')
