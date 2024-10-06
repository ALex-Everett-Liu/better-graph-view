import sqlite3

'''replace'''
# Define the string to search for and the replacement string
old_string = 'whitespace character \s \s'
new_string = 'whitespace character \s'

# Connect to the database
conn = sqlite3.connect('graph_data.db')
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

'''clear'''
# Connect to the database
conn = sqlite3.connect('graph_data.db')
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
