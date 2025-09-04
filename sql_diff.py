import argparse
import sqlparse
import re
import os
import sys

def normalize_statement(statement):
    # Remove comments and whitespace
    return sqlparse.format(statement, strip_comments=True, keyword_case='upper').strip()

def get_object_identifier(statement):
    """
    Extracts a unique identifier for a SQL object from its statement.
    Returns a tuple like ('TABLE', 'public.my_table') or ('FUNCTION', 'public.my_function')
    """
    
    # Function
    match = re.search(r"CREATE(?: OR REPLACE)? FUNCTION ([\w\.]+) \(", statement, re.IGNORECASE)
    if match:
        return ('FUNCTION', match.group(1).strip())

    # Table
    match = re.search(r"CREATE TABLE ([\w\.]+) \(", statement, re.IGNORECASE)
    if match:
        return ('TABLE', match.group(1).strip())

    # Index
    match = re.search(r"CREATE (?:UNIQUE )?INDEX (.*?) ON", statement, re.IGNORECASE)
    if match:
        return ('INDEX', match.group(1).strip())

    # View
    match = re.search(r"CREATE VIEW (.*?) AS", statement, re.IGNORECASE)
    if match:
        return ('VIEW', match.group(1).strip())

    # Sequence
    match = re.search(r"CREATE SEQUENCE (.*?) ", statement, re.IGNORECASE)
    if match:
        return ('SEQUENCE', match.group(1).strip())

    # Constraint
    match = re.search(r"ALTER TABLE .*? ADD CONSTRAINT (.*?) ", statement, re.IGNORECASE)
    if match:
        return ('CONSTRAINT', match.group(1).strip())
        
    # Alter table
    match = re.search(r"ALTER TABLE (.*?) ", statement, re.IGNORECASE)
    if match:
        return ('ALTER TABLE', match.group(1).strip())

    # Fallback for other statements
    return None

def parse_sql(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # First, remove all comments from the file
    content = sqlparse.format(content, strip_comments=True)
    
    statements = sqlparse.split(content)
    objects = {}
    
    for stmt in statements:
        normalized_stmt = normalize_statement(stmt)
        if not normalized_stmt:
            continue
            
        # Ignore certain statements
        if any(keyword in normalized_stmt for keyword in ['SET ', 'SELECT pg_catalog.set_config', 'ALTER SEQUENCE']):
            continue

        identifier = get_object_identifier(normalized_stmt)
        
        if identifier:
            objects[identifier] = normalized_stmt
        elif not normalized_stmt.startswith('DROP'):
            objects[('UNKNOWN', normalized_stmt)] = normalized_stmt
            
    return objects

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.stderr.write(f'error: {message}\n')
        sys.exit(2)

def main():
    parser = CustomArgumentParser(description='Compare two SQL dump files or directories.')
    parser.add_argument('-f', '--files', nargs=2, help='Two SQL files to compare.')
    parser.add_argument('-d', '--directories', nargs=2, help='Two directories to compare.')
    parser.add_argument('-s', '--syntax', choices=['pg15', 'pg16', 'gbq', 'sqlite3'], default='pg15', help='SQL syntax for the output.')
    args = parser.parse_args()

    if args.files:
        old_dump, new_dump = args.files
        diff, has_differences = compare_files(old_dump, new_dump, args.syntax)
        if diff:
            print('\n'.join(diff))
        sys.exit(1 if has_differences else 0)
    elif args.directories:
        compare_directories(args.directories[0], args.directories[1], args.syntax)
    else:
        parser.print_help()

def compare_files(old_dump, new_dump, syntax):
    try:
        old_objects = parse_sql(old_dump)
        new_objects = parse_sql(new_dump)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(-1)
    except Exception as e:
        print(f"Error parsing SQL: {e}", file=sys.stderr)
        sys.exit(-1)

    old_keys = set(old_objects.keys())
    new_keys = set(new_objects.keys())

    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys
    common_keys = old_keys.intersection(new_keys)

    diff = []
    has_differences = False

    if added_keys or removed_keys or any(old_objects[key] != new_objects[key] for key in common_keys):
        has_differences = True

    # Removed objects
    for key in sorted(list(removed_keys)):
        object_type, object_name = key
        if object_type == 'TABLE':
            diff.append(f"DROP TABLE IF EXISTS {object_name};")
        elif object_type == 'FUNCTION':
            diff.append(f"DROP FUNCTION IF EXISTS {object_name};")
        elif object_type == 'INDEX':
            diff.append(f"DROP INDEX IF EXISTS {object_name};")
        elif object_type == 'VIEW':
            diff.append(f"DROP VIEW IF EXISTS {object_name};")
        elif object_type == 'SEQUENCE':
            diff.append(f"DROP SEQUENCE IF EXISTS {object_name};")
        elif object_type == 'CONSTRAINT':
            diff.append(f"-- Cannot auto-generate DROP for CONSTRAINT {object_name}. Manual intervention required.")
        else:
            diff.append(f"-- Don't know how to drop object of type {object_type} with name {object_name}")

    # Added objects
    for key in sorted(list(added_keys)):
        diff.append(f"{new_objects[key]};")

    # Modified objects
    for key in sorted(list(common_keys)):
        if old_objects[key] != new_objects[key]:
            diff.append(f"-- MODIFIED: {key[0]} {key[1]}")
            if key[0] in ('FUNCTION', 'VIEW'):
                diff.append(f"DROP {key[0]} IF EXISTS {key[1]};")
                diff.append(f"{new_objects[key]};")
            elif key[0] == 'TABLE':
                old_table = parse_create_table(old_objects[key])
                new_table = parse_create_table(new_objects[key])
                alter_statements = generate_alter_table(old_table, new_table, syntax)
                if alter_statements:
                    diff.extend(alter_statements)
            elif key[0] == 'INDEX':
                diff.append(f"DROP INDEX IF EXISTS {key[1]};")
                diff.append(f"{new_objects[key]};")

    return diff, has_differences

def parse_create_table(statement):
    table = {'name': None, 'columns': {}, 'constraints': {}}
    
    # Extract table name
    match = re.search(r"CREATE TABLE ([\w\.]+) \(", statement, re.IGNORECASE)
    if not match:
        return table
    table['name'] = match.group(1).strip()

    # Extract the content between the first '(' and the last ')'
    try:
        content = statement[statement.find('(') + 1 : statement.rfind(')')]
    except IndexError:
        return table

    # This is a simplistic approach. A proper parser would be needed for complex cases.
    # We'll split by comma, but need to handle commas inside parentheses (e.g., for function calls)
    
    # A simple way to handle this is to find commas at the top level of parenthesis nesting
    parts = []
    paren_level = 0
    current_part = ""
    for char in content:
        if char == '(':
            paren_level += 1
        elif char == ')':
            paren_level -= 1
        
        if char == ',' and paren_level == 0:
            parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
    parts.append(current_part.strip())


    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Normalize whitespace
        part = re.sub(r'\s+', ' ', part)

        if part.upper().startswith('CONSTRAINT') or part.upper().startswith('PRIMARY KEY') or part.upper().startswith('FOREIGN KEY') or part.upper().startswith('UNIQUE'):
            # Handle constraints
            match = re.search(r"(?:CONSTRAINT (.*?) )?(.*)", part, re.IGNORECASE)
            if match:
                constraint_name = match.group(1)
                constraint_def = match.group(2).strip()
                if not constraint_name:
                    constraint_name = f"{table['name']}_{len(table['constraints'])}"
                table['constraints'][constraint_name] = constraint_def
        else:
            # Handle columns
            # This regex is still not perfect, but it's a step forward
            match = re.match(r"(\w+)\s+(.*?)(?:(NOT NULL)|(DEFAULT .*?))?((?:NOT NULL)|(?:DEFAULT .*?))?$", part, re.IGNORECASE)
            
            # A better approach for columns
            words = part.split()
            column_name = words[0]
            
            column_details = {
                'type': words[1], # This is a simplification
                'not_null': False,
                'default': None
            }

            # Check for NOT NULL
            if 'NOT' in words and 'NULL' in words:
                column_details['not_null'] = True
            
            # Check for DEFAULT
            if 'DEFAULT' in words:
                default_index = words.index('DEFAULT')
                column_details['default'] = ' '.join(words[default_index+1:])

            # Reconstruct type without other keywords
            type_words = []
            for i, word in enumerate(words[1:]):
                if word.upper() in ('NOT', 'NULL', 'DEFAULT'):
                    break
                type_words.append(word)
            column_details['type'] = ' '.join(type_words)


            table['columns'][column_name] = column_details
            
    return table


def generate_alter_table(old_table, new_table, syntax):
    alter_statements = []
    table_name = old_table['name']

    syntax_templates = {
        'pg15': {
            'add_column': "ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};",
            'drop_column': "ALTER TABLE {table_name} DROP COLUMN {column_name};",
            'rename_column': "ALTER TABLE {table_name} RENAME COLUMN {old_column_name} TO {new_column_name};",
            'alter_column_type': "ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {column_type};",
            'set_default': "ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT {default_value};",
            'drop_default': "ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP DEFAULT;",
            'set_not_null': "ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL;",
            'drop_not_null': "ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL;",
            'add_constraint': "ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} {constraint_def};",
            'drop_constraint': "ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name};",
        },
    }

    templates = syntax_templates.get(syntax, syntax_templates['pg15'])

    old_columns = old_table['columns']
    new_columns = new_table['columns']
    
    old_column_names = set(old_columns.keys())
    new_column_names = set(new_columns.keys())

    added_columns = new_column_names - old_column_names
    removed_columns = old_column_names - new_column_names
    common_columns = old_column_names.intersection(new_column_names)

    # Heuristic for renamed columns: find a removed and added column with the same type
    possible_renames = {}
    # Make copies of the sets to modify them
    added_columns_copy = added_columns.copy()
    removed_columns_copy = removed_columns.copy()

    for rem_col in removed_columns_copy:
        for add_col in added_columns_copy:
            # A very simple heuristic: if types are similar. This could be improved.
            if old_columns[rem_col]['type'] == new_columns[add_col]['type']:
                possible_renames[rem_col] = add_col
                # Remove them from the sets so we don't also generate ADD/DROP statements
                added_columns.remove(add_col)
                removed_columns.remove(rem_col)
                break
    
    for old_name, new_name in possible_renames.items():
        alter_statements.append(templates['rename_column'].format(table_name=table_name, old_column_name=old_name, new_column_name=new_name))
        # Since we've renamed the column, we should now compare the other attributes (like NOT NULL, DEFAULT)
        # using the new name. We'll add the renamed column to the common_columns set for this purpose.
        common_columns.add(new_name)
        # We also need the old definition under the new name for comparison
        old_columns[new_name] = old_columns.pop(old_name)


    for col in added_columns:
        col_def = new_columns[col]['type']
        if new_columns[col]['not_null']:
            col_def += " NOT NULL"
        if new_columns[col]['default'] is not None:
            col_def += f" DEFAULT {new_columns[col]['default']}"
        alter_statements.append(templates['add_column'].format(table_name=table_name, column_name=col, column_def=col_def))

    for col in removed_columns:
        alter_statements.append(templates['drop_column'].format(table_name=table_name, column_name=col))

    for col in common_columns:
        # Type change
        if old_columns[col]['type'] != new_columns[col]['type']:
            alter_statements.append(templates['alter_column_type'].format(table_name=table_name, column_name=col, column_type=new_columns[col]['type']))
        
        # Default value change
        if old_columns[col]['default'] != new_columns[col]['default']:
            if new_columns[col]['default'] is not None:
                alter_statements.append(templates['set_default'].format(table_name=table_name, column_name=col, default_value=new_columns[col]['default']))
            else:
                alter_statements.append(templates['drop_default'].format(table_name=table_name, column_name=col))

        # NOT NULL change
        if old_columns[col]['not_null'] != new_columns[col]['not_null']:
            if new_columns[col]['not_null']:
                alter_statements.append(templates['set_not_null'].format(table_name=table_name, column_name=col))
            else:
                alter_statements.append(templates['drop_not_null'].format(table_name=table_name, column_name=col))


    # Compare constraints
    old_constraints = set(old_table['constraints'].keys())
    new_constraints = set(new_table['constraints'].keys())

    added_constraints = new_constraints - old_constraints
    removed_constraints = old_constraints - new_constraints

    for con in added_constraints:
        alter_statements.append(templates['add_constraint'].format(table_name=table_name, constraint_name=con, constraint_def=new_table['constraints'][con]))

    for con in removed_constraints:
        alter_statements.append(templates['drop_constraint'].format(table_name=table_name, constraint_name=con))

    return alter_statements


def compare_directories(old_dir, new_dir, syntax):
    old_files = {}
    for root, _, files in os.walk(old_dir):
        for file in files:
            if file.endswith('.sql'):
                path = os.path.join(root, file)
                relative_path = os.path.relpath(path, old_dir)
                old_files[relative_path] = path

    new_files = {}
    for root, _, files in os.walk(new_dir):
        for file in files:
            if file.endswith('.sql'):
                path = os.path.join(root, file)
                relative_path = os.path.relpath(path, new_dir)
                new_files[relative_path] = path

    old_paths = set(old_files.keys())
    new_paths = set(new_files.keys())

    common_paths = old_paths.intersection(new_paths)
    added_paths = new_paths - old_paths
    removed_paths = old_paths - new_paths

    differences_found = False
    all_diffs = []

    for path in sorted(list(common_paths)):
        all_diffs.append(f"-- Comparing files: {path}")
        diff, has_differences = compare_files(old_files[path], new_files[path], syntax)
        if has_differences:
            differences_found = True
            all_diffs.extend(diff)

    for path in sorted(list(added_paths)):
        all_diffs.append(f"-- New file: {path}")
        with open(new_files[path], 'r') as f:
            all_diffs.append(f.read())
        differences_found = True

    for path in sorted(list(removed_paths)):
        all_diffs.append(f"-- Removed file: {path}")
        all_diffs.append(f"-- To remove the objects in this file, you may need to manually create DROP statements.")
        differences_found = True

    if all_diffs:
        print('\n'.join(all_diffs))

    if differences_found:
        sys.exit(1)
    else:
        sys.exit(0)



if __name__ == '__main__':
    main()
