# SQL Diff

A command-line tool to identify differences between two SQL dumps and generate a patch file.

## Features

*   Compare two individual SQL files.
*   Recursively compare two directories containing `.sql` files.
*   Generate a valid SQL patch file to apply to the "left-side" database.
*   Supports multiple SQL syntaxes (currently PostgreSQL).
*   Detects changes in tables, functions, views, indexes, and sequences.
*   Generates `ALTER TABLE` statements for modified tables, including:
    *   Adding, dropping, and renaming columns.
    *   Changing column types.
    *   Modifying `NOT NULL` constraints.
    *   Updating `DEFAULT` values.

## Installation

### User Installation

You can install the application from the root of the project directory using `pip`:

```bash
pip install .
```

This will install the `sql-diff` command-line tool in your environment.

### Administrator/Developer Installation

For development, it's recommended to use a virtual environment.

1.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    ```

2.  **Activate the virtual environment:**

    *   On macOS and Linux:

        ```bash
        source venv/bin/activate
        ```

    *   On Windows:

        ```bash
        .\venv\Scripts\activate
        ```

3.  **Install the package in editable mode:**

    ```bash
    pip install -e .
    ```

    This allows you to make changes to the source code and have them immediately reflected when you run the tool.

## Testing

To run the tests, execute the test script from the root of the project:

```bash
python tests/test_sql_diff.py
```

For more comprehensive test runs, you can use a test runner like `pytest`:

```bash
pip install pytest
pytest
```

## Building

This project uses `pyproject.toml` for a modern build process.

1.  **Install the build tool:**

    ```bash
    pip install build
    ```

2.  **Build the package:**

    ```bash
    python -m build
    ```

This will create a `dist/` directory containing the source distribution (`.tar.gz`) and a wheel (`.whl`) file, which can be distributed and installed in other environments.

## Usage

The `sql-diff` tool can be used in two modes: file comparison and directory comparison.

### Case 1: Comparing Two Files

```bash
sql-diff -f <old_file.sql> <new_file.sql>
```

This will compare the two specified SQL files and print the generated SQL patch to standard output.

### Case 2: Comparing Two Directories

```bash
sql-diff -d <old_directory> <new_directory>
```

This will recursively compare all `.sql` files in the two directories. It will compare files with the same relative path in each directory.

### Options

*   `-s, --syntax`: Specify the SQL syntax for the output.
    *   `pg15` (default): PostgreSQL 15
    *   `pg16`: PostgreSQL 16
    *   `gbq`: Google BigQuery
    *   `sqlite3`: SQLite 3

## Return Codes

*   `0`: No differences were found.
*   `1`: Differences were found.
*   `-1`: An error occurred (e.g., file not found, parsing error).

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more details.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
