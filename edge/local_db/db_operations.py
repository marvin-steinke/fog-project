import sqlite3
import os
from sqlite3 import Error
import threading
import logging

# TODO: (Niklas Fomin, 2023-06-08) add type hints, docstrings, and logging

class dbHandler:
    """This is a class for handling db-operations using SQLite3."""
    def __init__(self, local_db_file: str):
        """Init the db connection

        Args:
            local_db_file (str): takes path to local db file
        """
        self.db_file = local_db_file
        self.thread_local = threading.local()
        
    def get_connection(self) -> sqlite3.Connection:
        """Get the db connection
        
        Returns:
            sqlite3.Connection: db connection to local.db
        """
        db_path = os.path.join(os.path.dirname(__file__), '..', 'local.db')
        if not hasattr(self.thread_local, "conn") or self.thread_local.conn is None:
            self.thread_local.conn = sqlite3.connect(self.db_file)
        return self.thread_local.conn
    
    def close_connection(self):
        """Terminate the db connection"""
        if hasattr(self.thread_local, "conn") and self.thread_local.conn is not None:
            self.thread_local.conn.close()
            self.thread_local.conn = None
           
    def create_schema(self):
        """Create the schema to store the incoming kafka topics"""
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS power_averages (
                    id INTEGER PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    average REAL NOT NULL,
                    sequence_number INTEGER DEFAULT 0,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    sent INTEGER DEFAULT 0
                    );
            ''')
            connection.commit()
            logging.info("household schema was created")
        except Error as e:
            logging.error(f"Error while creating schema: {e}")
            
    def insert_power_average(self, node_id: str, average: float) -> int:
        """Add a new average to the created schema

        Args:
            node_id (str): identifier for household node (sensor)
            average (float): the average power

        Returns:
            int: id of row   
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            #timestamp = datetime.now(pytz.timezone('Europe/Stockholm')).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                    INSERT INTO power_averages(id, node_id, average, sequence_number, sent)
                VALUES (NULL, ?, ?,0,0);
            ''', (node_id, average))
            connection.commit()
            #self.close_connection()
            logging.info(f"Inserted power average for node_id {node_id} successfully.")
            return cursor.lastrowid
        except Error as e:
            logging.error(f"Error while inserting power average: {e}")


    def update_sent_flag(self, id: int):
        """Update db table when data is sent successfully
        Args:
            id (int): id of row to update (sent = 1
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                    UPDATE power_averages
                    SET sent = 1
                    WHERE id = ?;
                ''', (id,))
            connection.commit()
            logging.info(f"Updated power average with id {id} successfully.")
        except Error as e:
            logging.error(f"Error while updating power average: {e}")
            
    def update_to_ack(self, id: int):
        """Update db table when data is acknowledged
        Args:
            id (int): id of row to update (sent = 2)
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            # Here, "sent" is updated to 2, meaning the data has been sent and acknowledged
            cursor.execute('''
                    UPDATE power_averages
                    SET sent = 2
                    WHERE id = ?;
                ''', (id,))
            connection.commit()
            logging.info(f"Updated power average with id {id} as acknowledged.")
        except Error as e:
            logging.error(f"Error while updating power average as acknowledged: {e}") 
                   
    def get_unsent_power_averages(self):
        """Fetch rows that have not been sent.
        Returns:
            List: list of tuples with unsent power averages
        """
        connection = self.get_connection()  
        try:
            cursor = connection.cursor()
            cursor.execute('''
                    SELECT id, node_id, average, timestamp FROM power_averages
                    WHERE sent = 0;
                ''')
            return cursor.fetchall()
        except Error as e:
            logging.error(f"Error while fetching unsent power averages: {e}")
            return []
    
    def get_unacknowledged_power_averages(self):
        """Fetch rows that have not been acknowledged.
        Returns:
            List: list of tuples with unacknowledged power averages
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                    SELECT id, node_id, average, timestamp FROM power_averages
                    WHERE sent = 1;
                ''')
            return cursor.fetchall()
        except Error as e:
            logging.error(f"Error while fetching unacknowledged power averages: {e}")
            return []
    
    def update_sequence_number(self, id: int):
        """Update the sequence_number attribute of a power average row.

        Args:
            id (int): The id of the power average row to update.
            sequence_number (int): The new sequence number value.
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute('''
                UPDATE power_averages
                SET sequence_number = ?
                WHERE id = ?;
            ''', (id, id))
            connection.commit()
            logging.info(f"Updated sequence number for power average with id {id} successfully.")
        except Error as e:
            logging.error(f"Error while updating sequence number for power average: {e}")
                    
    def truncate_table(self, table_name: str):
        """Truncates a table in the database.

        Args:
            table_name (str): name of the table that should be cleared after usage.
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(f"DELETE FROM {table_name};")
            connection.commit()
            logging.info(f"The table '{table_name}' has been truncated.")
        except Error as e:
            logging.error(f"An error occurred while truncating the table '{table_name}': {e}")