from visualization import find_and_plot_multiple_nodes
import tkinter as tk
import os
import sqlite3
# from database import initialize_database, DB_PATH

# Specify the database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'graph_data.db')

def connect_to_database():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    return conn

def main():
    conn = connect_to_database()
    print(f"Connected to database at {DB_PATH}")
    
    root = tk.Tk()
    root.title("Graph Builder")
    root.geometry("500x200")  # Set window size root.geometry("500x350")

    style = {
        'font': ('Montserrat', 15),
        'width': 25,
        'height': 2,
        'bg': '#2B7396',
        'fg': 'lightgreen',
    }
    
    multiple_nodes_button = tk.Button(root, text="Compare 5 Nodes", command=lambda: find_and_plot_multiple_nodes(root), **style)
    multiple_nodes_button.pack(pady=10)

    conn.close()
    
    root.mainloop()

if __name__ == "__main__":
    main()