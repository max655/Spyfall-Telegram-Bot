import json
import pymssql
from contextlib import closing

with open('credentials.json', 'r') as f:
    credentials = json.load(f)

server = credentials.get("SERVER")
database = credentials.get("DATABASE")
login = credentials.get("LOGIN")
password = credentials.get("PASSWORD")


def connect_db():
    conn = pymssql.connect(server=server,
                           database=database,
                           user=login,
                           password=password)
    conn.autocommit(True)
    return conn


def create_table():
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE Places (
               id INT,
               dictionary_id INT,
               name NVARCHAR(25)
            )
        ''')
            cursor.execute('''
            CREATE TABLE DictionaryPlaces (
               dictionary_id INT,
               place_id INT
            )
        ''')
            cursor.execute('''
            CREATE TABLE Dictionaries (
               id INT,
               name INT,
               place NVARCHAR(25)
            )
        ''')

