import argparse
import os
import sqlite3
from flask import Flask, request, jsonify
from flask_caching import Cache
import pandas as pd
import re

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


class Config:
    DEBUG = False
    SERVER_PORT = 3000
    DATA_FOLDER = 'data'
    DB_FOLDER = 'dbs'


class DatabaseManager:
    @staticmethod
    def get_db_path(db_name):
        return os.path.join(Config.DB_FOLDER, db_name + '.sqlite3')

    @staticmethod
    def open_connection(db_name):
        return sqlite3.connect(DatabaseManager.get_db_path(db_name))

    @staticmethod
    def execute_query(db_name, query, fetch_all=True, args=[]):
        with sqlite3.connect(DatabaseManager.get_db_path(db_name)) as conn:
            cursor = conn.cursor()
            cursor.execute(query, args)
            return cursor.fetchall() if fetch_all else cursor.fetchone()

    @staticmethod
    def attach_all_databases(main_conn):
        for db_file in os.listdir(Config.DB_FOLDER):
            if db_file.endswith('.sqlite3'):
                db_name = os.path.splitext(db_file)[0]
                db_path = DatabaseManager.get_db_path(db_name)
                main_conn.execute(f'ATTACH DATABASE "{db_path}" AS {db_name}')


@app.route('/api', methods=['GET'])
def api_documentation():
    documentation = {
        '/api/update': {
            'method': 'GET',
            'description': 'Updates databases with new data from CSV files.',
            'parameters': None,
            'returns': 'JSON object with status message and list of updates.',
            'example_api': f'GET http://localhost:{Config.SERVER_PORT}/api/update',
            'example_cli': 'python main.py -update'
        },
        '/api/databases': {
            'method': 'GET',
            'description': 'Lists all databases, providing details such as name, row count, size, and number of columns.',
            'parameters': None,
            'returns': 'JSON object with status, error message (if any), and a list of database details.',
            'example_api': f'GET http://localhost:{Config.SERVER_PORT}/api/databases',
            'example_cli': 'python main.py -databases'
        },
        '/api/show': {
            'method': 'GET',
            'description': 'Displays the first few rows of a specified table in a database.',
            'parameters': 'name (string, required), limit (int, optional, default=5)',
            'returns': 'JSON array of the first few rows in the specified table.',
            'example_api': f'GET http://localhost:{Config.SERVER_PORT}/api/show?name=table_name&limit=5',
            'example_cli': 'python main.py -show TABLE_NAME'
        },
        '/api/sql': {
            'method': 'GET',
            'description': 'Executes a given SQL query across all databases and returns the results.',
            'parameters': 'sql (string, required)',
            'returns': 'JSON array of query results, with each row represented as a dictionary.',
            'example_api': f'GET http://localhost:{Config.SERVER_PORT}/api/sql?sql=SQL_QUERY',
            'example_cli': 'python main.py -sql "SQL_QUERY"'
        }
    }
    return jsonify(documentation)


@app.route('/api/databases', methods=['GET'])
def list_databases():
    try:
        db_files = [f for f in os.listdir(Config.DB_FOLDER) if f.endswith('.sqlite3')]
        if not db_files:
            return jsonify({"status": "error", "error": "No databases found."}), 404

        databases = []
        for db_file in db_files:
            db_name = os.path.splitext(db_file)[0]
            db_path = os.path.join(Config.DB_FOLDER, db_file)

            # Query to get tables in the database
            query = "SELECT name FROM sqlite_master WHERE type='table';"
            tables = DatabaseManager.execute_query(db_name, query)

            # Initialize variables to accumulate rows and columns across all tables
            total_rows = 0
            total_columns = 0

            # Gather information for each table
            for table_name in tables:
                # Count rows in the table
                row_query = f"SELECT COUNT(*) FROM {table_name[0]};"
                row_count = DatabaseManager.execute_query(db_name, row_query, False)[0]
                total_rows += row_count

                # Count columns in the table
                column_query = f"PRAGMA table_info({table_name[0]});"
                columns = DatabaseManager.execute_query(db_name, column_query)
                total_columns += len(columns)

            # Get the size of the database file in kilobytes
            size_kb = os.path.getsize(db_path) / 1024

            # Add database information to the response
            databases.append({
                "name": db_name,
                "rows": total_rows,
                "columns": total_columns,
                "size": size_kb
            })

        return jsonify({"status": "success", "databases": databases})

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500



@app.route('/api/update', methods=['GET'])
def update_databases():
    try:
        updates = []
        for file in os.listdir(Config.DATA_FOLDER):
            if file.endswith('.csv'):
                db_name = file.replace('.csv', '')
                df = pd.read_csv(os.path.join(
                    Config.DATA_FOLDER, file), encoding='utf-8')
                with DatabaseManager.open_connection(db_name) as conn:
                    df.to_sql(name=db_name, con=conn,
                              if_exists='replace', index=False)
                updates.append(f"{db_name} updated.")
        return jsonify({"message": "Databases updated.", "updates": updates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/show', methods=['GET'])
def show_table_api():
    table_name = request.args.get('name', type=str)
    limit = request.args.get('limit', default=5, type=int)
    data, error, status_code = show_table_head(table_name, limit)
    if error:
        return jsonify({"error": error}), status_code
    return jsonify(data), status_code


@app.route('/api/sql', methods=['GET'])
@cache.cached(timeout=10, query_string=True)
def execute_sql():
    sql_query = request.args.get('sql', type=str)

    if not sql_query:
        return jsonify({"error": "Missing 'sql' parameter"}), 400

    db_files = [file for file in os.listdir(
        Config.DB_FOLDER) if file.endswith('.sqlite3')]
    if not db_files:
        return jsonify({"error": "No databases found."}), 404

    db_names = [os.path.splitext(file)[0] for file in db_files]
    main_db = db_names[0]

    results = []
    try:
        with DatabaseManager.open_connection(main_db) as conn:
            cursor = conn.cursor()

            for db_name in db_names[1:]:
                conn.execute(f'ATTACH DATABASE "{os.path.join(Config.DB_FOLDER, db_name + ".sqlite3")}" AS {db_name}')

            cursor.execute(sql_query)
            rows = cursor.fetchall()

            for db_name in db_names[1:]:
                conn.execute(f'DETACH DATABASE {db_name}')

            if rows:
                columns = [column[0] for column in cursor.description]
                results.extend([dict(zip(columns, row)) for row in rows])
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(results)


def show_table_head_cli(table_name, limit=5):
    conn = DatabaseManager.open_connection(table_name)
    with conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
    return jsonify([dict(zip(columns, row)) for row in rows])


def show_table_head(table_name, limit=5):
    try:
        query = f"SELECT * FROM {table_name} LIMIT {limit};"
        rows = DatabaseManager.execute_query(table_name, query)
        if not rows:
            return None, "Table not found or is empty", 404

        with DatabaseManager.open_connection(table_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row)) for row in rows], None, 200
    except sqlite3.Error as e:
        return None, str(e), 500


def extract_db_names_from_query(sql_query):
    pattern = re.compile(r'\b\w+\.')
    potential_dbs = pattern.findall(sql_query)
    return set([db.strip('.') for db in potential_dbs])


def cli_handler():
    global DEBUG
    global SERVER_PORT

    parser = argparse.ArgumentParser()
    parser.add_argument('-debug', action='store_true',
                        default=Config.DEBUG, help='Enable debug mode')
    parser.add_argument('-port', type=int, default=Config.SERVER_PORT,
                        help='Port to run the application on')
    parser.add_argument('-databases', action='store_true',
                        help='List databases')
    parser.add_argument('-api', action='store_true',
                        help='Show API documentation')
    parser.add_argument('-show', metavar='TABLE_NAME', help='Show table head')
    parser.add_argument('-update', action='store_true',
                        help='Update databases')
    parser.add_argument('-sql', metavar='SQL_QUERY', help='Execute SQL query')
    args = parser.parse_args()

    if args.databases:
        print(list_databases().get_data(as_text=True))
    elif args.api:
        print(api_documentation().get_data(as_text=True))
    elif args.show:
        data, error, _ = show_table_head(args.show)
        if error:
            print(f"Error: {error}")
        else:
            print(data)
    elif args.update:
        print(update_databases().get_data(as_text=True))
    elif args.sql:
        sql_query = args.sql

        try:
            specified_databases = extract_db_names_from_query(sql_query)
            with DatabaseManager.open_connection(next(iter(specified_databases))) as conn:

                for db_name in specified_databases:
                    db_name = db_name.strip()
                    db_path = DatabaseManager.get_db_path(db_name)
                    conn.execute(f'ATTACH DATABASE "{db_path}" AS {db_name}')

                cursor = conn.cursor()
                cursor.execute(sql_query)
                rows = cursor.fetchall()
                if rows:
                    columns = [column[0] for column in cursor.description]
                    for row in rows:
                        print(dict(zip(columns, row)))
        except sqlite3.Error as e:
            print(f"SQL Error: {e}")

    else:
        Config.DEBUG = args.debug
        Config.SERVER_PORT = args.port
        app.run(debug=Config.DEBUG, port=Config.SERVER_PORT)


if __name__ == '__main__':
    if not os.path.exists(Config.DATA_FOLDER):
        os.makedirs(Config.DATA_FOLDER)
    if not os.path.exists(Config.DB_FOLDER):
        os.makedirs(Config.DB_FOLDER)
    cache.init_app(app)
    cli_handler()
