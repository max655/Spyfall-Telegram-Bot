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
               FOREIGN KEY (place_id) REFERENCES Dictionaries(id),
               PRIMARY KEY (dictionary_id, place_id)
            )
            ''')


def insert_data():
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()

            cursor.execute("INSERT INTO Dictionaries (name) VALUES ('Офіс')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES ('Пляж')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES ('Університет')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES ('Супермаркет')")
            cursor.execute("INSERT INTO Dictionaries (name) VALUES ('Ресторан')")

            cursor.execute("INSERT INTO Places (name) VALUES ('Конференц-зал')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Кабінет')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Відділ IT')")

            cursor.execute("INSERT INTO Places (name) VALUES ('Басейн')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Тераса')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Бар')")

            cursor.execute("INSERT INTO Places (name) VALUES ('Бібліотека')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Лабораторія')")

            cursor.execute("INSERT INTO Places (name) VALUES ('Каса')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Коридор з полицями')")

            cursor.execute("INSERT INTO Places (name) VALUES ('Зал зі столиками')")
            cursor.execute("INSERT INTO Places (name) VALUES ('Кухня')")

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
            return cursor.fetchall()


def view_table(table):
    with closing(connect_db()) as db:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {table}')
            rows = cursor.fetchall()
            for row in rows:
                print(row)


if __name__ == "__main__":
    view_table('Places')
    places = get_places_for_dictionary(5)
    print(places)
