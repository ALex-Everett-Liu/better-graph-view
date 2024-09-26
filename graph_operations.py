import tkinter as tk
from tkinter import simpledialog, messagebox, font
import sqlite3
from database import DB_PATH
import networkx as nx

def add_node_and_edges():
    node_name = simpledialog.askstring("Input", "Enter the node name:")
    if not node_name:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO nodes (name) VALUES (?)", (node_name,))
    
    while True:
        related_node_input = simpledialog.askstring("Input", f"Enter a related node and distance for {node_name} (format: 'Node B, 5') (or cancel to finish):")
        if not related_node_input:
            break
        
        try:
            related_node, weight = [x.strip() for x in related_node_input.split(',')]
            weight = float(weight)
        except ValueError:
            messagebox.showerror("Error", "Invalid input format. Please enter in the format 'Node B, 5'.")
            continue
        
        c.execute("INSERT OR IGNORE INTO nodes (name) VALUES (?)", (related_node,))
        
        c.execute("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)",
                  (node_name, related_node, weight))
        c.execute("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)",
                  (related_node, node_name, weight))

    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Node and edges added successfully!")

def get_graph_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    G = nx.Graph()
    
    c.execute("SELECT source, target, weight FROM edges")
    for row in c.fetchall():
        G.add_edge(row[0], row[1], weight=row[2])
    
    conn.close()
    return G 
