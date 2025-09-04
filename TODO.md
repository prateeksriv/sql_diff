# Future Implementation Ideas for sql_diff

This file lists potential features and improvements for the `sql_diff` tool that are currently out of scope but could be implemented in the future.

### More Comprehensive Schema Comparison

*   **Additional Database Object Types**:
    *   **Triggers**: Compare triggers on tables.
    *   **User-Defined Types (UDTs)**: Diff custom data types.
    *   **Grants and Permissions**: Detect differences in user roles and permissions.
    *   **Table Partitions**: Compare table partitioning schemes.
    *   **Collations and Character Sets**: Check for differences in default character sets and collations.

*   **Complex Object Modifications**:
    *   **Sequence modifications**: Handle changes to sequence properties like increment value, start value, etc.

### Smarter Diff Generation

*   **Dependency Management**: Build a dependency graph of all database objects to generate `DROP` and `CREATE` statements in the correct topological order, avoiding errors due to dependencies.
*   **Transactionality**: Wrap the entire generated SQL diff script in a single transaction (`BEGIN; ... COMMIT;`) to ensure all changes are applied atomically.

### Data Comparison

*   **Data Diff**: Add an option to compare the actual data within the tables, not just the schema.

### Usability and Robustness

*   **Wider SQL Dialect Support**: Improve parsing and diff generation for more SQL dialects beyond PostgreSQL.
*   **Configuration File**: Allow for more complex comparison rules and configurations via a config file.
*   **Testing**: Implement a comprehensive test suite with unit and integration tests.
