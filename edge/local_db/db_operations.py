import sqlite3
import os
from sqlite3 import Error
import threading

# TODO: (Niklas Fomin, 2023-06-08) add type hints, docstrings, and logging

class dbHandler:
    """This is a class for handling db-operations using SQLite3."""
    def __init__(self, local_db_file):
        """Init the db connection

        Args:
            local_db_file (str): takes path to local db file
        """
        self.db_file = local_db_file
        self.thread_local = threading.local()
        
    def get_connection(self):
        """Get the db connection"""
        db_path = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        if not hasattr(self.thread_local, "conn") or self.thread_local.conn is None:
            self.thread_local.conn = sqlite3.connect(self.db_file)
        return self.thread_local.conn
        '''
        try:
            self.conn = sqlite3.connect(local_db_file)
        except Error as e:
            print(e)
            
        if self.conn:
            self.create_schema()
        '''
           
    def create_schema(self):
        """Create the schema for the db"""
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS power_averages (
                    id INTEGER PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    average REAL NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    sent INTEGER DEFAULT 0
                    );
            ''')
            connection.commit()
        except Error as e:
            print(e)
            
    
    def insert_power_average(self, node_id, average):
        """Add a new average to the created schema

        Args:
            node_id (_type_): _description_
            average (_type_): _description_
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                    INSERT INTO power_averages(id, node_id, average)
                VALUES (NULL, ?, ?);
            ''', (node_id, average))
            connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(e)
            
    def update_power_average(self, id):
        """Update db table when data is sent successfully"""
        connection = self.get_connection()
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                    UPDATE power_averages
                    SET sent = 1
                    WHERE id = ?;
                ''', (id,))
            connection.commit()
        except Error as e:
            print(e)
            
    def get_unsent_power_averages(self):
        """Fetch rows that have not been sent."""
        connection = self.get_connection()  
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                    SELECT id, node_id, average, timestamp FROM power_averages
                    WHERE sent = 0;
                ''')
            return cursor.fetchall()
        except Error as e:
            print(e)
            return []
                    

