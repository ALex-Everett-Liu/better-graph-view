import tkinter as tk
from tkinter import simpledialog, messagebox, font
import sqlite3
from database import DB_PATH
import networkx as nx

class MultilineDialog(simpledialog.Dialog):
    def body(self, master):
        self.result = None
        tk.Label(master, text="Enter nodes and their related nodes with weights:").grid(row=0)
        self.entry = tk.Text(master, width=50, height=10)
        self.entry.grid(row=1, padx=5, pady=5)
        return self.entry

    def apply(self):
        self.result = self.entry.get("1.0", tk.END).strip()

def ask_multiline(title, prompt, **kwargs):
    dialog = MultilineDialog(None, title=title)
    return dialog.result

def add_node_and_edges():
    nodes_input = ask_multiline("Input", "Enter nodes and their related nodes with weights:\n"
                                         "(format: NodeA: NodeB, 5, NodeC, 10\n"
                                         "         NodeD: NodeE, 7, NodeF, 12\n"
                                         "         ...)\n"
                                         "Enter each node on a new line:", parent=None, multiline=True)
    if not nodes_input:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for line in nodes_input.split('\n'):
        line = line.strip()
        if not line:
            continue

        try:
            node_name, relations = line.split(':')
            node_name = node_name.strip()
            relations = relations.strip()
            related_nodes = [x.strip() for x in relations.split(',')]
        except ValueError:
            messagebox.showerror("Error", f"Invalid input format in line: {line}\n"
                                          "Please use the format: NodeA: NodeB, 5, NodeC, 10")
            continue

        c.execute("INSERT OR IGNORE INTO nodes (name) VALUES (?)", (node_name,))

        for i in range(0, len(related_nodes), 2):
            try:
                related_node = related_nodes[i]
                weight = float(related_nodes[i+1])
            except (IndexError, ValueError):
                messagebox.showerror("Error", f"Invalid input for related node or weight: {', '.join(related_nodes[i:i+2])}")
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
