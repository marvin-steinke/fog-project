import sqlite3
import os
from sqlite3 import Error

class dbHandler:
    """This is a class for handling db-operations using SQLLite3."""
    def __init__(self, local_db_file):
        """Init the db connection

        Args:
            local_db_file (str): takes path to local db file
        """
        self.db_file = local_db_file
        self.conn = None
        try:
            if not os.path.exists(self.db_file):
                self.create_schema
            self.conn = sqlite3.connect(local_db_file)
        except Error as e:
            print(e)
            
        if self.conn:
            self.create_schema()
            
    def create_schema(self):
        """Create the schema for the db"""
        
        try:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS power_averages (
                    id INTEGER PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    average REAL NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
        except Error as e:
            print(e)
    
    def insert_power_average(self, node_id, average):
        """Add a new average to the created schema

        Args:
            node_id (_type_): _description_
            average (_type_): _description_
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                    INSERT INTO power_averages(node_id, average)
                VALUES (?, ?);
            ''', (node_id, average))
            self.conn.commit()
        except Error as e:
            print(e)
            
test_db_handler = dbHandler('test.db')

