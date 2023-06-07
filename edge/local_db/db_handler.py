import sqlite3
from sqllite3 import Error

class dbHandler:
    """This is a class for handling db-operations using SQLLite3."""
    def __init__(self, db_file):
        """Init the db connection

        Args:
            db_file (_type_): _description_
        """
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_file)
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