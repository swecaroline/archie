import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError
from server import ServerRecord

connection = None

def refresh_connection():
    load_dotenv()
    DB_NAME = os.getenv('DB_NAME')
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')

    global connection
    connection = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        sslmode='require'
    )
    connection.autocommit = True

def execute_query(connection, query):
    connection.autocommit = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def execute_read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def init_db():
    create_servers_table = """
    CREATE TABLE IF NOT EXISTS servers (
    id BIGINT PRIMARY KEY,
    archiveId BIGINT NOT NULL, 
    timeToArchive INTEGER,
    timeToDelete INTEGER
    );
    """

    create_permanent_categories_table = """
    CREATE TABLE IF NOT EXISTS permanentCategories (
    id BIGINT PRIMARY KEY,
    serverID BIGINT
    );
    """
    execute_query(connection, create_servers_table)
    execute_query(connection, create_permanent_categories_table)

def read_server_values(id):

    select_server = (f"SELECT * FROM servers WHERE id={id}")

    refresh_connection()
    server = execute_read_query(connection, select_server)

    if(len(server) > 0):
        serverRow = server[0]

        return ServerRecord(
            id=serverRow[0],
            archiveId=serverRow[1],
            timeToArchive=serverRow[2],
            timeToDelete=serverRow[3]
        )

    else:
        return None

def upsert_server(id, **kwargs):
    refresh_connection()

    valid_keys = ["archiveId", "timeToArchive", "timeToDelete"]
    new_keys = []
    new_values = []
    
    for key in valid_keys:
    
        new_keys.append(key)
        value = kwargs.get(key)
        if (value == None):
            print("Appending none")
            new_values.append('NULL')
        else:
            new_values.append(value)

    print("NEW VALUES" + str(new_values))

    def get_update_str(key):
        value = kwargs.get(key)
        if (value == None):
            value = 'NULL'
        return f"{key} = {value}"

    query = f"""
    INSERT INTO servers (id, {",".join(map(str, new_keys))})
    VALUES ({id}, {",".join(map(str, new_values))})
    ON CONFLICT (id)
    DO UPDATE SET 
    {",".join(map(get_update_str, new_keys))}
    """
    print("UPSERT QUERY: " + query)

    cursor = connection.cursor()
    try:
        cursor.execute(query, new_values)
        connection.commit()
        print("Query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

def delete_server_record(id):
    delete_query = f"""
    DELETE FROM servers WHERE id={id};
    DELETE FROM permanentCategories WHERE serverID={id};
    """
    cursor = connection.cursor()
    try:
        cursor.execute(delete_query)
        connection.commit()
        print("Delete query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

refresh_connection()
init_db()
