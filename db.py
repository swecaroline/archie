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
    archive TEXT NOT NULL, 
    timeout INTEGER,
    permanent_categories TEXT,
    permanent_channels TEXT,
    delete_time INTEGER
    )
    """
    execute_query(connection, create_servers_table)

def upsertServerConfig(id, category, timeout):

    if timeout:
        vars = {"param_id": id, "param_category": category, "param_timeout": timeout}
        insert_query = "INSERT INTO servers (id, archive, timeout) VALUES (%(param_id)s, %(param_category)s, %(param_timeout)s) ON CONFLICT (id) DO UPDATE SET archive = %(param_category)s, timeout = %(param_timeout)s;"
    else:
        vars = {"param_id": id, "param_category": category}
        insert_query = "INSERT INTO servers (id, archive) VALUES (%(param_id)s, %(param_category)s) ON CONFLICT (id) DO UPDATE SET archive = %(param_category)s;"

    refresh_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(insert_query, vars)
        connection.commit()
    except Exception as e:
        print(f"The error '{e}' occurred")
        updateServer(id, archive=category, timeout=timeout)

def readServerValues(id):

    select_server = (f"SELECT * FROM servers WHERE id={id}")

    refresh_connection()
    server = execute_read_query(connection, select_server)

    if(len(server) > 0):
        serverRow = server[0]
        permanentCategories = []
        if (serverRow[3] != None):
            permanentCategories = serverRow[3].split('\n')
        permanentChannels = []
        if (serverRow[4] != None):
            permanentChannels = serverRow[4].split('\n')

        return ServerRecord(
            id=serverRow[0],
            archiveCategoryName=serverRow[1],
            timeToArchive=serverRow[2],
            permanentCategories=permanentCategories,
            permanentChannels=permanentChannels,
            timeToDeletion=serverRow[5]
        )

    else:
        return None

def updateServer(id, **kwargs):

    update_server = "UPDATE servers\nSET "
    count = 0

    refresh_connection()

    new_values = []
    
    for key in kwargs:
    
        if(key == "archive"):
            update_server += "archive = %s"
        elif(key=="timeout"):
            if(kwargs.get(key) != 'NULL'):
                update_server += "timeout = %s"
            else:
                update_server += "timeout = NULL"
        elif(key=="permanent_categories"):
            if(kwargs.get(key) != 'NULL'):
                update_server += "permanent_categories = %s"
            else:
                update_server += "permanent_categories = NULL"
        elif(key=="delete_time"):
            if(kwargs.get(key) != 'NULL'):
                update_server += "delete_time = %s"
            else:
                update_server += "delete_time = NULL"

        new_values.append(kwargs.get(key))

        count += 1
        if(count == len(kwargs)):
            update_server += "\n"
        else:
            update_server += ",\n"

    update_server += f"WHERE id = {id}"

    cursor = connection.cursor()
    try:
        cursor.execute(update_server, new_values)
        connection.commit()
        print("Query executed successfully")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

refresh_connection()
init_db()
