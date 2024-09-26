import os
import shutil
import sqlite3

# Specify the database file paths
EXISTING_DB_PATH = os.path.join(os.path.dirname(__file__), 'existing_graph_data.db')
DB_PATH = os.path.join(os.path.dirname(__file__), 'graph_data.db')

def initialize_database():
    if os.path.exists(EXISTING_DB_PATH) and not os.path.exists(DB_PATH):
        shutil.copy2(EXISTING_DB_PATH, DB_PATH)
        print(f"Existing database copied from {EXISTING_DB_PATH} to {DB_PATH}")
    elif not os.path.exists(DB_PATH):
        create_database()
        print(f"New database created at {DB_PATH}")
    else:
        print(f"Using existing database at {DB_PATH}")

def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS nodes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS edges
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT, target TEXT, weight REAL,
                  UNIQUE(source, target))''')
    conn.commit()
    conn.close()

