# ServeLite Documentation

```
    Work in progress
```

ServeLite is a versatile application that serves as a Python database with Flask. It offers a CLI with customizable arguments, utilizes SQLite3 as its database engine, and supports a file-based database structure.

## Installation

To set up ServeLite, simply run the `install` script.

```
    install.bat
```

The script will install Python if you don't have it, clone the repository, and set up everything for you.

## Usage

### Starting ServeLite

You can start ServeLite with a single click:

```
    start.bat
```

Alternatively, you can start it in the terminal using the following command:

```
    py main.py
```

## API Endpoints

ServeLite provides the following API endpoints:

### /api/databases (GET)

```
Method: GET
Description: Lists all databases, providing details such as name, row count, size, and number of columns.
Returns: JSON object with a status, error message (if any), and a list of database details.
Example API Request: GET http://localhost:3000/api/databases
Example CLI Command: python main.py -databases
```

### /api/update (POST)

```
Method: POST
Description: Updates databases with new data from CSV files.
Returns: JSON object with a status message and a list of updates.
Example API Request: POST http://localhost:3000/api/update
Example CLI Command: python main.py -update
```

### /api/show (GET)

```
Method: GET
Description: Displays the first few rows of a specified table in a database.
Parameters: name (string, required), limit (int, optional, default=5)
Returns: JSON array of the first few rows in the specified table.
Example API Request: GET http://localhost:3000/api/show?name=table_name&limit=5
Example CLI Command: python main.py -show TABLE_NAME
```

### /api/sql (GET)

```
Method: GET
Description: Executes a given SQL query across all databases and returns the results.
Parameters: sql (string, required)
Returns: JSON array of query results, with each row represented as a dictionary.
Example API Request: GET http://localhost:3000/api/sql?sql=SQL_QUERY
Example CLI Command: python main.py -sql "SQL_QUERY"
```

## CLI Commands

ServeLite provides a command-line interface (CLI) with the following commands:

Show API Documentation

```
    python main.py -api
```

List Databases

```
    python main.py -databases
```

Update Databases

```
    python main.py -update
```

Show Table Head

```
    python main.py -show TABLE_NAME
```

Execute SQL Query

```
    python main.py -sql "SQL_QUERY"
```

## Configuration

You can configure ServeLite by modifying the Config class in the main.py file. The available configuration options include:

- `DEBUG` (Default: `False`): Enable or disable debug mode.
- `SERVER_PORT` (Default: `3000`): Specify the port on which the application runs.
- `DATA_FOLDER` (Default: `data`): The folder where CSV data files are stored.
- `DB_FOLDER` (Default: `dbs`): The folder where SQLite3 database files are stored.

## Database Management

ServeLite uses SQLite3 as its database engine and supports a file-based database structure. You can manage databases and tables using SQL queries.
