import sqlite3
from collections import defaultdict
import os

def create_or_update_database(filename, db_name='text_chunks.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS nodes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS edges
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  source TEXT, target TEXT, weight REAL,
                  UNIQUE(source, target))''')

    # Dictionary to store edges
    edges = {}

    # Read from file and insert or update database
    with open(filename, 'r') as file:
        for line in file:
            parts = line.strip().split(':')
            if len(parts) == 2:
                source = parts[0].strip()
                connections = parts[1].strip().split(',')

                # Insert source node
                cursor.execute('INSERT OR IGNORE INTO nodes (name) VALUES (?)', (source,))

                for i in range(0, len(connections), 2):
                    target = connections[i].strip()
                    weight = float(connections[i+1].strip())

                    # Insert target node
                    cursor.execute('INSERT OR IGNORE INTO nodes (name) VALUES (?)', (target,))

                    # Store edge in dictionary
                    edges[(source, target)] = weight

    # Insert edges and their reverse edges
    for (source, target), weight in edges.items():
        # Insert forward edge
        cursor.execute('''INSERT OR REPLACE INTO edges (source, target, weight)
                          VALUES (?, ?, ?)''', (source, target, weight))

        # Insert reverse edge if not explicitly provided
        if (target, source) not in edges:
            cursor.execute('''INSERT OR REPLACE INTO edges (source, target, weight)
                              VALUES (?, ?, ?)''', (target, source, weight))

    # Commit changes and close connection
    conn.commit()
    conn.close()

def read_file(filename):
    graph = defaultdict(dict)
    with open(filename, 'r') as file:
        for line in file:
            parts = line.strip().split(':')
            if len(parts) == 2:
                source = parts[0].strip()
                connections = parts[1].strip().split(',')
                for i in range(0, len(connections), 2):
                    target = connections[i].strip()
                    weight = int(connections[i+1].strip())
                    
                    # Add the forward relation
                    graph[source][target] = weight
                    
                    # Add the reverse relation if it doesn't exist
                    if target not in graph or source not in graph[target]:
                        graph[target][source] = weight

    return graph

def get_related_chunks(db_name, start_chunk, max_depth=3):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    related = defaultdict(float)
    queue = [(start_chunk, 0)]
    visited = set()

    for depth in range(max_depth):
        new_queue = []
        for current, current_weight in queue:
            if current != start_chunk:
                related[current] = max(related[current], current_weight)

            cursor.execute('''SELECT target, weight FROM edges WHERE source = ?''', (current,))
            for neighbor, edge_weight in cursor.fetchall():
                if neighbor not in visited:
                    new_queue.append((neighbor, edge_weight))
                    visited.add(neighbor)

        queue = new_queue
        if not queue:
            break

    conn.close()
    return related

def print_related_chunks(related):
    sorted_related = sorted(related.items(), key=lambda x: (x[1], x[0]))
    for chunk, weight in sorted_related:
        print(f"{chunk}, {weight}")


# Main execution
filename = 'text_chunks_01.txt'
db_name = 'text_chunks.db'
# graph = read_file(filename)

# Check if database exists, if not, create it
if not os.path.exists(db_name):
    print("Creating new database...")
else:
    print("Updating existing database...")

# Create or update the database from the text file
create_or_update_database(filename, db_name)

while True:
    start_chunk = input("Enter the starting chunk (or 'quit' to exit): ")
    if start_chunk.lower() == 'quit':
        break

    related_chunks = get_related_chunks(db_name, start_chunk)

    print(f"\nChunks related to {start_chunk} (within 3 steps):")
    print_related_chunks(related_chunks)
    print()

print("Goodbye!")
