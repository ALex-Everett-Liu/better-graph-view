import sqlite3
import networkx as nx

# Connect to the database
conn = sqlite3.connect('graph_data.db')
c = conn.cursor()

# Function to search for records with a keyword
def search_edges(keyword):
    # SQL query to search for the keyword in source or target columns
    query = """
    SELECT id, source, target, weight 
    FROM edges 
    WHERE source LIKE ? OR target LIKE ?
    """
    
    # Execute the query
    c.execute(query, ('%' + keyword + '%', '%' + keyword + '%'))
    
    # Fetch all matching records
    results = c.fetchall()
    
    # Print the results
    if results:
        print(f"Found {len(results)} record(s) matching '{keyword}':")
        for row in results:
            print(f"ID: {row[0]}, Source: {row[1]}, Target: {row[2]}, Weight: {row[3]}")
    else:
        print(f"No records found matching '{keyword}'")

# Example usage
search_keyword = 'xxx'  # Replace 'xxx' with your desired keyword
search_edges(search_keyword)

# Close the connection
conn.close()
