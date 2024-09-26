import tkinter as tk
from tkinter import simpledialog, messagebox, font
import sqlite3
import networkx as nx
import numpy as np
import pandas as pd
import statistics
from heapq import nsmallest
import os
import shutil
import random
from graph_operations import get_graph_from_db

def find_nearest_nodes(): 
    G = get_graph_from_db()
    node = simpledialog.askstring("Input", "Enter the node name to find nearest nodes:")
    if node not in G.nodes():
        messagebox.showerror("Error", f"Node '{node}' not found in the graph.")
        return

    distances = nx.single_source_dijkstra_path_length(G, node)
    nearest_nodes = nsmallest(31, distances.items(), key=lambda x: x[1])  # Get top 21 (including the node itself)
    nearest_nodes = [n for n in nearest_nodes if n[0] != node][:30]  # Exclude the node itself and get top 20

    result = "\n".join([f"{i+1}. {n[0]}: {n[1]}" for i, n in enumerate(nearest_nodes)])
    # messagebox.showinfo("Nearest Nodes", f"Top 20 nearest nodes to {node}:\n\n{result}")
    # Create a custom messagebox with larger font
    result_window = tk.Toplevel()
    result_window.title(f"Top 20 nearest nodes to {node}")
    result_window.geometry("500x600")
    
    text_widget = tk.Text(result_window, font=("Roboto", 14), wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    text_widget.insert(tk.END, result)
    text_widget.config(state=tk.DISABLED)

    # Plot the local graph
    # plot_local_graph(node, nearest_nodes)
    
def calculate_node_metrics(G, center_nodes):
    results = {
        'Node': [],
        'Connected Nodes': [],
        'Distance 5': [],
        'Distance 10': [],
        'Distance 20': []
    }
    
    for node in center_nodes:
        # Number of directly connected nodes (degree)
        degree = G.degree(node)

        # Calculate distances to all other nodes
        lengths = nx.single_source_dijkstra_path_length(G, node)

        # Exclude the node itself and sort distances to other nodes
        sorted_lengths = sorted(lengths.values())[1:]

        # Calculate average distances for top 5, 10, and 20 nearest nodes
        avg_dist_top5 = sum(sorted_lengths[:5]) / min(5, len(sorted_lengths))
        avg_dist_top10 = sum(sorted_lengths[:10]) / min(10, len(sorted_lengths))
        avg_dist_top20 = sum(sorted_lengths[:20]) / min(20, len(sorted_lengths))

        # Append results to the dictionary
        results['Node'].append(node)
        results['Connected Nodes'].append(degree) # Directly Connected Nodes
        results['Distance 5'].append(avg_dist_top5) # Average Distance to Top 5 Nearest
        results['Distance 10'].append(avg_dist_top10)
        results['Distance 20'].append(avg_dist_top20)
    
    return pd.DataFrame(results)

def display_metrics(df):
    result_window = tk.Toplevel()
    result_window.title("Node Metrics")
    result_window.geometry("700x400")

    text_widget = tk.Text(result_window, font=("Arial", 12), wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    text_widget.insert(tk.END, df.to_string())
    text_widget.config(state=tk.DISABLED)

def calculate_edge_statistics():
    G = get_graph_from_db()
    edge_weights = [data['weight'] for u, v, data in G.edges(data=True)]

    if edge_weights:
        average_weight = sum(edge_weights) / len(edge_weights)
        median_weight = statistics.median(edge_weights)

        messagebox.showinfo("Edge Statistics", f"Average Edge Weight: {average_weight:.2f}\nMedian Edge Weight: {median_weight:.2f}")
    else:
        messagebox.showinfo("Edge Statistics", "No edges found in the graph.")
