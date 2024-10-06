import sqlite3

def replace_text_in_db(db_path, old_string, new_string):
    """
    Replace occurrences of old_string with new_string in all text columns of the database.

    :param db_path: Path to the SQLite database file.
    :param old_string: String to search for.
    :param new_string: String to replace with.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        
        # Get the list of columns for the current table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            
            # Check if the column is of a text type
            if column_type.lower() in ['text', 'varchar', 'char', 'clob']:
                # Update the column by replacing the old string with the new string
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET {column_name} = REPLACE({column_name}, ?, ?)
                    WHERE {column_name} LIKE ?;
                """, (old_string, new_string, f'%{old_string}%'))
        
        # Commit the changes for the current table
        conn.commit()

    # Close the connection
    conn.close()

def clear_database(db_path):
    """
    Clear all data from all tables in the database.

    :param db_path: Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Disable foreign key constraints temporarily
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # Begin transaction
    cursor.execute("BEGIN TRANSACTION;")

    # Get the list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Generate and execute DELETE statements for each table
    for table in tables:
        cursor.execute(f"DELETE FROM {table[0]};")

    # Commit the transaction
    conn.commit()

    # Re-enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Close the connection
    conn.close()

def main():
    db_path = 'graph_data.db'
    
    # Example usage of replace_text_in_db
    old_string = 'whitespace character \s \s'
    new_string = 'whitespace character \s'
    replace_text_in_db(db_path, old_string, new_string)
    
    # Example usage of clear_database
    clear_database(db_path)

if __name__ == "__main__":
    main()
