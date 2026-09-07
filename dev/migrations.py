import os
from db import execute_read_query, set_permanent_categories, upsert_server
from dotenv import load_dotenv
import psycopg2

from utils import get_category

load_dotenv()
DB_NAME = os.getenv('HEROKU_DB_NAME')
DB_USERNAME = os.getenv('HEROKU_DB_USERNAME')
DB_PASSWORD = os.getenv('HEROKU_DB_PASSWORD')
DB_HOST = os.getenv('HEROKU_DB_HOST')
DB_PORT = os.getenv('HEROKU_DB_PORT')

heroku_connection = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    sslmode='require'
)
heroku_connection.autocommit = True

def migrate_sept_2026(guild):
    id = guild.id
    select_server = (f"SELECT * FROM servers WHERE id={id}")

    server = execute_read_query(heroku_connection, select_server)

    if(len(server) > 0):
        server_row = server[0]
        server_id = server_row[0]
        archiveCategoryName = server_row[1]
        permanent_category_names = server_row[3]
        if (permanent_category_names == None):
            permanent_category_names = []
        else:
            permanent_category_names = permanent_category_names.split('\n')
        time_to_archive = server_row[2]
        time_to_delete = server_row[5]

        archive_category = get_category(guild=guild, name=archiveCategoryName)

        def name_to_id(name: str):
            category = get_category(guild=guild, name=name)
            if (category != None):
                return category.id
            else:
                return None

        permanent_category_ids = list(map(name_to_id, permanent_category_names))
        permanent_category_ids = list(filter(lambda val: val != None, permanent_category_ids))
        if (archive_category != None):
            upsert_server(
                id=server_id, 
                archiveId=archive_category.id, 
                timeToArchive=time_to_archive,
                timeToDelete=time_to_delete
            )

            if (len(permanent_category_ids) > 0):
                set_permanent_categories(permanent_category_ids, server_id)

    print("Sucessfully migrated data from server id " + str(guild.id))

async def debug_activeservers(activeservers, TEST_SERVER_ID):
    for guild in activeservers:
        # migrate_sept_2026(guild)
        id = guild.id
        if (str(id) == str(TEST_SERVER_ID)):
            print("Found test server")
            if (len(guild.categories) < 30):
                for i in range(30 - len(guild.categories)):
                    await guild.create_category(f"Test {i}")