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


def create_tables():
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE Dictionaries (
               id INT IDENTITY(1,1) PRIMARY KEY,
               name NVARCHAR(50) NOT NULL
            )
            ''')
            cursor.execute('''
            CREATE TABLE Places (
               id INT IDENTITY(1,1) PRIMARY KEY,
               name NVARCHAR(50) NOT NULL
            )
            ''')
            cursor.execute('''
            CREATE TABLE DictionaryPlaces (
               dictionary_id INT,
               place_id INT,
               FOREIGN KEY (dictionary_id) REFERENCES Dictionaries(id),
               FOREIGN KEY (place_id) REFERENCES Places(id),
               PRIMARY KEY (dictionary_id, place_id)
            )
            ''')


def insert_data():
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()

            cursor.execute("INSERT INTO Dictionaries (name) VALUES (N'Офіс')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES (N'Пляж')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES (N'Університет')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES (N'Супермаркет')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES (N'Ресторан')")

            cursor.execute("INSERT INTO Places (name) VALUES (N'Конференц-зал')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Кабінет')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Відділ IT')")

            cursor.execute("INSERT INTO Places (name) VALUES (N'Басейн')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Тераса')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Бар')")

            cursor.execute("INSERT INTO Places (name) VALUES (N'Бібліотека')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Лабораторія')")

            cursor.execute("INSERT INTO Places (name) VALUES (N'Каса')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Коридор з полицями')")

            cursor.execute("INSERT INTO Places (name) VALUES (N'Зал зі столиками')")
            cursor.execute("INSERT INTO Places (name) VALUES (N'Кухня')")


def insert_connections():
    with closing(connect_db()) as db:
        with db as conn:
            try:
                cursor = conn.cursor()

                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (1, 1)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (1, 2)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (1, 3)")

                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (2, 4)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (2, 5)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (2, 6)")

                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (3, 2)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (3, 7)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (3, 8)")

                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (4, 9)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (4, 10)")

                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (5, 11)")
                cursor.execute("INSERT INTO DictionaryPlaces (dictionary_id, place_id) VALUES (5, 12)")
            except pymssql.Error as e:
                print("An error occurred:", e)
                conn.rollback()


def get_places_for_dictionary(dictionary_id):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT p.name
            FROM Places p
            LEFT JOIN DictionaryPlaces dp ON p.id = dp.place_id
            LEFT JOIN Dictionaries d ON dp.dictionary_id = d.id
            WHERE d.id = %s
            ''', (dictionary_id,))
            result = cursor.fetchall()
            return [row[0] for row in result]


def get_dictionary_name(dictionary_id):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name from Dictionaries WHERE id = %s', (dictionary_id,))
            row = cursor.fetchone()
            return row[0] if row else None


def fetch_table(table):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table}')
            rows = cursor.fetchall()
            return rows


def fetch_constraints():
    query = '''
    SELECT 
        tc.constraint_type,
        tc.table_name,
        tc.constraint_name
    FROM 
        INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
    WHERE 
        tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
    ORDER BY 
        CASE 
            WHEN tc.constraint_type = 'FOREIGN KEY' THEN 1 
            ELSE 2 
        END
    '''

    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()


def drop_constraints(constraints):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            for constraint_type, table_name, constraint_name in constraints:
                drop_query = f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"
                print(f"Executing: {drop_query}")
                cursor.execute(drop_query)
            print("All specified constraints have been dropped.")


def drop_table(table_name):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(f'DROP TABLE {table_name}')


if __name__ == "__main__":
    """constraints = fetch_constraints()
    drop_constraints(constraints)

    drop_table('Dictionaries')
    drop_table('Places')
    drop_table('DictionaryPlaces')

    create_tables()
    insert_data()

    constraints = fetch_constraints()
    print("All constraints:")
    for constraint in constraints:
        print(constraint)"""

    rows = fetch_table('Places')
    for row in rows:
        print(row)

    rows = fetch_table('Dictionaries')
    for row in rows:
        print(row)

    places = get_places_for_dictionary(1)
    print(places)
