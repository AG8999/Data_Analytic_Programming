import requests
import csv
import logging
from io import StringIO
from pymongo import MongoClient, errors
import psycopg2
from psycopg2 import sql
import atexit

class ApiHandler:
    """Class to handle api query
    """
    def __init__(self, api_url):
        self.api_url = api_url
    
    def api_request_data(self):
        """ 
        This is a function to request a call to any api
        Parameters:
            - api_url = url
        """
        try:
            # API request
            response = requests.get(self.api_url)
            print("API call in progress...")
            if response.status_code == 200:
                # Determine the type of response is JSON or CSV
                content_type = response.headers.get('Content-Type', '').lower()

                if 'json' in content_type:
                    # If it's JSON, parse and return as a dictionary
                    print("Data api return a json file")
                    return response.json()
                elif 'csv' in content_type:
                    # If it's CSV, parse and return as a list of dictionaries
                    print("Data api return a csv file")
                    csv_data = response.text
                    csv_reader = csv.DictReader(StringIO(csv_data))
                    return list(csv_reader)
                else:
                    # If not recognized, raise an exception
                    raise ValueError(f"Unsupported content type: {content_type}")

            else:
                # If request was not successful, raise an exception
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            # Handle any exceptions during request
            print(f"Error making API call: {e}")
   
class DataMongoHandler:
    """ This is a class for handling all Mongo data operations.
            - Connecting to database
            - Inserting the data into database
    """
    def __init__(self, mongo_uri, database_name, collection_name):
        self.mongo_uri = mongo_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.collection = self.connect_to_mongodb()

        # Register cleanup function to be called on program exit
        atexit.register(self.cleanupDB)

    
    def connect_to_mongodb(self):
        """ 
        This is a function to connect mongodb database
        Parameters:
            - mongo_uri = mongo_uri
            - database_name = database_name
            - collection_name = collection_name 
        """
        try:
            # Connect to MongoDB
            self.client = MongoClient(self.mongo_uri)
            db = self.client[self.database_name]
            collection = db[self.collection_name]

            # Check the connection if it is successful
            server_info = self.client.server_info()
            print("<====== Connected to MongoDB successfully. =======> \n")
            print(f"Server Info: {server_info} \n")
            return collection

        except errors.ConnectionFailure as e:
            # Error Handler
            print(f"Failed to connect to MongoDB: {e} \n ")
            return None

        except Exception as e:
            # Handle other exceptions if necessary
            print(f"An error occurred: {e}")

    
    def cleanupDB(self):
        """
        This function is clean up the resource, after our work
        Close the connection for MongoDB and PostgreSQL
        """
        # Close the MongoDB connection
        if getattr(self, 'client', None):
            self.client.close()
            print("<====== Connection to MongoDB closed. =======> \n")
            
    def load_data_to_mongodb(self, database_name, db_list, data, collection,unique_key , chunk_size=1000):
        """ 
        This is a function to insert data in batch to mongo database
        Parameters:
            - db_name = "your_database_name"
            - db_list = client.list_database_names()
            - collection = client[db_name][your_collection_name]
            - chunk_size = 5000
            - data = "actual_data
        """
        try:
            if database_name in db_list:
                logging.info(f'The {database_name} database exists.')
                print(f'The {database_name} database exists.')
                # Insert data if not exist
                print("FILTERING NEW OR UPDATED RECORD.....")
                total_documents = len(data)
                batch = 0
                documents_to_insert = []
    
                for i in range(0, total_documents, chunk_size):
                    chunk = data[i:i + chunk_size]

                    for document in chunk:
                        if unique_key not in document or not collection.find_one({unique_key: document[unique_key]}):
                            documents_to_insert.append(document)
    
                    batch += 1
                    print(f"Number of New or updated data from batch {batch}: {len(documents_to_insert)} documents.")
    
                if documents_to_insert:
                    result = collection.insert_many(documents_to_insert, ordered=False)
                    logging.info(f"Inserted {len(result.inserted_ids)} documents.")
                    print(f"Inserted {len(result.inserted_ids)} documents.")
                else:
                    logging.info("No new data to insert.")
                    print("No new data to insert.")
            else:
                logging.info(f'The {database_name} database not exists.')
                print(f'The {database_name} database not exists.')
                print(" LOADING DATA TO MONGODB..............")
                load_to_mongo = collection.insert_many(data)
                print("DATA LOADED SUCCESSFULLY......!")
                #client = collection.database.client
                #db_list = client.list_database_names()   
                #print(db_list)
        except errors.PyMongoError as e:
            logging.error(f"Failed to interact with MongoDB: {e}")
            print(f"Failed to interact with MongoDB: {e}")

class PostgresHandler:
    """Class to establish connection in PostgreSQL and operations
    """
    def __init__(self, pg_config):
        """Intializing the connection
            Parameters:
            - pg_config = {
                    'host': 'postgresql',
                    'database': 'db_ecommerce',
                    'user': 'dap_group',
                    'password': 'dap_group',
                    'port': '5432'
                }
        """
        try:
            print('<===== Connecting to the PostgreSQL database... ======> \n')
            self.connection = psycopg2.connect(**pg_config)
            self.cursor = self.connection.cursor()
            print("<===== Connected to PostgreSQL successfully. =====> \n")
        except psycopg2.Error as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            return None

    def create_table(self, table_name, columns):
        """Create table in database
            Parameters:
            - table_name = 'test-data'
            - columns = '{'actual_price': 'INT', 'average_rating': 'FLOAT', 'brand': 'VARCHAR(255)','
        """
        try:
            columns_sql = [sql.SQL("{} {}").format(sql.Identifier(column), sql.SQL(data_type)) for column, data_type in columns.items()]
            create_table_query = sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                sql.Identifier(table_name), sql.SQL(', ').join(columns_sql)
            )
            self.cursor.execute(create_table_query)
            self.connection.commit()
            print(f"Table {table_name} created successfully.")
        except Exception as e:
            print(f"Error creating table {table_name}: {e}")
            
    def table_info(self, table_name):
        """Get table schema information, by firing query
            Parameters:
            - table_name = 'test-data'
        """
        try:
            # Retrieve table information from information_schema.columns
            get_table_info_query = sql.SQL("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = {}
            """).format(sql.Literal(table_name))
            
            self.cursor.execute(get_table_info_query)
            columns_info = self.cursor.fetchall()

            return columns_info
        except Exception as e:
            print(f"Error getting table information for {table_name}: {e}")
            return None

    def table_exists(self, table_name):
        """This method checks if the table exists in the tables
            Parameters:
            - table_name = 'test-data'
        """
        try:
            check_table_query = sql.SQL("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = {})").format(
                sql.Literal(table_name)
            )
            self.cursor.execute(check_table_query)
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"Error checking if table {table_name} exists: {e}")
            return False

    def insert_data_frame(self, table_name, data_frame, unique_key=None):
        """This method run queries to insert our data into the table
            Parameters:
            - table_name = 'test-data'
            - data_frame = 'df'
            - unique_key = None
        """
        try:
            if unique_key:
                # Check for duplicates based on the unique_key before insertion
                existing_data_query = sql.SQL("SELECT {} FROM {}").format(
                    sql.Identifier(unique_key), sql.Identifier(table_name)
                )
                self.cursor.execute(existing_data_query)
                existing_keys = {row[0] for row in self.cursor.fetchall()}
                new_data_frame = data_frame[~data_frame[unique_key].isin(existing_keys)]
            else:
                new_data_frame = data_frame

            if not new_data_frame.empty:
                columns = list(new_data_frame.columns)
                values = new_data_frame.values.tolist()
                insert_query = sql.SQL("INSERT INTO {} ({}) VALUES {}").format(
                    sql.Identifier(table_name),
                    sql.SQL(', ').join(map(sql.Identifier, columns)),
                    sql.SQL(', ').join([sql.SQL('(') + sql.SQL(', ').join(map(sql.Literal, row)) + sql.SQL(')') for row in values])
                )
                self.cursor.execute(insert_query)
                self.connection.commit()
                print(f"Data inserted into {table_name} successfully.")
            else:
                print("No new data to insert.")
        except Exception as e:
            print(f"Error inserting data into {table_name}: {e}")

    def execute_query(self, query):
        """This method to query any data from the table
            Parameters:
            - query = "SELECT * FROM TABLE" (Pass any SQL query)
        """
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    def close_connection(self):
        """This method is to close the connection, once we have performed our operations
        """
        self.cursor.close()
        self.connection.close()
        print("<====== Connection to PostgreSQL closed. =======> \n") 