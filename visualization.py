import tkinter as tk
from tkinter import simpledialog, messagebox, font
import sqlite3
import networkx as nx
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statistics
from heapq import nsmallest
import os
import shutil
import random

DB_PATH = os.path.join(os.path.dirname(__file__), 'graph_data.db')

def get_graph_from_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    G = nx.Graph()
    
    c.execute("SELECT source, target, weight FROM edges")
    for row in c.fetchall():
        G.add_edge(row[0], row[1], weight=row[2])
    
    conn.close()
    return G 

def plot_combined_local_graph(center_nodes, nearest_nodes):
    G = get_graph_from_db()
    local_G = nx.Graph()
    
    # Add all center nodes and nearest nodes to the graph
    for node in center_nodes:
        local_G.add_node(node)
    for node, _ in nearest_nodes:
        local_G.add_node(node)
    
    # Add edges between center nodes and their nearest neighbors
    for center_node in center_nodes:
        for node, distance in nearest_nodes:
            if G.has_edge(center_node, node):
                local_G.add_edge(center_node, node, weight=G[center_node][node]['weight'])
    
    # Add edges between nearest nodes and their neighbors
    for node, _ in nearest_nodes:
        for neighbor in G.neighbors(node):
            if neighbor in [n[0] for n in nearest_nodes] or neighbor in center_nodes:
                local_G.add_edge(node, neighbor, weight=G[node][neighbor]['weight'])
    
    return local_G

def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2
    
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if denom == 0:
        return False
    
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    
    return 0 <= ua <= 1 and 0 <= ub <= 1

def adjust_node_position(pos, node, local_G, dx=None, dy=None):
    x, y = pos[node]
    if dx is None:
        dx = random.uniform(-0.1, 0.1)
    if dy is None:
        dy = random.uniform(-0.1, 0.1)
    pos[node] = (x + dx, y + dy)

def adjust_for_crossing(pos, u1, v1, u2, v2, step=0.03, max_attempts=20):
    original_positions = {node: pos[node] for node in [u1, v1, u2, v2]}
    
    for _ in range(max_attempts):
        # Try small adjustments
        for node in [u1, v1, u2, v2]:
            x, y = pos[node]
            for dx, dy in [(step, 0), (-step, 0), (0, step), (0, -step)]:
                pos[node] = (x + dx, y + dy)
                if not line_intersection((*pos[u1], *pos[v1]), (*pos[u2], *pos[v2])):
                    return True  # Crossing resolved
            pos[node] = (x, y)  # Reset if not resolved
    
    # If not resolved, revert to original positions
    for node, position in original_positions.items():
        pos[node] = position
    return False  # Couldn't resolve crossing

def nodes_too_close(pos, node1, node2, threshold=0.1):
    x1, y1 = pos[node1]
    x2, y2 = pos[node2]
    return abs(x1 - x2) < threshold and abs(y1 - y2) < threshold

def node_distance(pos, node1, node2):
    x1, y1 = pos[node1]
    x2, y2 = pos[node2]
    return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

def plot_combined_local_graph_2D(center_nodes, nearest_nodes, layout_type='spring', layout_params=None, skip_crossing_checks=False):
    local_G = plot_combined_local_graph(center_nodes, nearest_nodes)

    # Create a grid-based initial position
    n = len(local_G)
    cols = int(np.sqrt(n))
    rows = n // cols + (1 if n % cols else 0)
    initial_pos = {node: (i % cols, i // cols) for i, node in enumerate(local_G.nodes())}
    
    if layout_params is None:
        layout_params = {}

    if layout_type == 'custom':
        pos = layout_params.get('pos', nx.spring_layout(local_G))
    elif isinstance(layout_type, dict):
        pos = layout_type
    elif layout_type == 'spring':
        pos = nx.spring_layout(local_G, pos=initial_pos, **layout_params)
    elif layout_type == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(local_G, **layout_params)
    elif layout_type == 'spectral':
        pos = nx.spectral_layout(local_G, **layout_params)
    elif layout_type == 'circular':
        pos = nx.circular_layout(local_G, **layout_params)
    elif layout_type == 'shell':
        pos = nx.shell_layout(local_G, **layout_params)
    elif layout_type == 'spring_grid':
        pos = nx.spring_layout(local_G, pos=initial_pos, fixed=None, **layout_params)
    else:
        raise ValueError(f"Unknown layout type: {layout_type}")

    if not skip_crossing_checks:
        # Initialize variables
        max_iterations = 50
        iteration_count = 0

        # Check for edge crossings
        while iteration_count < max_iterations:
            adjustments_made = False
            edges = list(local_G.edges())
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    u1, v1 = edges[i]
                    u2, v2 = edges[j]
                    line1 = (*pos[u1], *pos[v1])
                    line2 = (*pos[u2], *pos[v2])
                    if line_intersection(line1, line2):
                        adjustments_made = adjust_for_crossing(pos, u1, v1, u2, v2) or adjustments_made

            iteration_count += 1

            if not adjustments_made:
                break  # Exit the loop if no adjustments were made

        if iteration_count == max_iterations:
            print(f"Warning: Maximum iterations ({max_iterations}) reached. Some edge crossings may remain.")

        # Detect and resolve edge crossings
        edges = list(local_G.edges())
        nodes = list(local_G.nodes())
        max_iterations = 50
        for _ in range(max_iterations):
            # crossings_found = False
            close_nodes_found = False
            
            # Check for close nodes
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    if nodes_too_close(pos, nodes[i], nodes[j]):
                        close_nodes_found = True
                        # Push one node away from the other
                        x1, y1 = pos[nodes[i]]
                        x2, y2 = pos[nodes[j]]
                        dx = 0.02 if x2 > x1 else -0.02
                        dy = 0.02 if y2 > y1 else -0.02
                        adjust_node_position(pos, nodes[j], local_G, dx, dy)
            
            # Check edge weights and node distances
            for u, v in local_G.edges():
                weight = local_G[u][v]['weight']
                distance = node_distance(pos, u, v)
                
                if weight > 7 and distance < 0.4:
                    adjustments_made = True
                    # Push nodes apart
                    x1, y1 = pos[u]
                    x2, y2 = pos[v]
                    dx = 0.1 if x2 > x1 else -0.1
                    dy = 0.1 if y2 > y1 else -0.1
                    adjust_node_position(pos, u, local_G, -dx, -dy)
                    adjust_node_position(pos, v, local_G, dx, dy)
                elif weight < 3 and distance > 0.4:
                    adjustments_made = True
                    # Pull nodes closer
                    x1, y1 = pos[u]
                    x2, y2 = pos[v]
                    dx = 0.03 if x2 > x1 else -0.03
                    dy = 0.03 if y2 > y1 else -0.03
                    adjust_node_position(pos, u, local_G, dx, dy)
                    adjust_node_position(pos, v, local_G, -dx, -dy)

            if not (close_nodes_found): # if not (crossings_found or close_nodes_found):
                break
    
    # Get edge weights
    edge_weights = [local_G[u][v]['weight'] for u, v in local_G.edges()]

    if edge_weights:
        # Normalize edge weights for line width
        max_weight = max(edge_weights)
        min_weight = min(edge_weights)
        weight_range = max_weight - min_weight
        normalized_weights = [(1 + max_weight - w) / weight_range for w in edge_weights]
        edge_widths = [1 + 7 * nw for nw in normalized_weights]  # Scale to 1-8 range
    else:
        edge_widths = []

    # Set up the plot
    plt.figure(figsize=(14, 8))
    
    # Draw edges
    nx.draw_networkx_edges(local_G, pos, width=edge_widths, edge_color='skyblue', alpha=0.6)
    
    # Draw nodes
    node_sizes = [50 + 100 * local_G.degree(node) for node in local_G.nodes()]  # Scale size based on degree
    node_colors = ['#d97706' if node in center_nodes else 'thistle' for node in local_G.nodes()]
    nx.draw_networkx_nodes(local_G, pos, node_size=node_sizes, node_color=node_colors)
    
    # Draw labels
    nx.draw_networkx_labels(local_G, pos, font_size=11)

    # Print edge weights at the center of each edge
    for (u, v), width in zip(local_G.edges(), edge_weights):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        plt.text(mid_x, mid_y, f'{width:.2f}', fontsize=8, ha='center', va='center', color='steelblue')
    
    # Set title
    plt.title(f'Combined Local Graph for {", ".join(center_nodes)}')
    
    # Remove axis
    plt.axis('off')
    
    # Show the plot
    plt.tight_layout()
    plt.show(block=False)
    
    # return pos  # Return the 2D coordinates
    return pos, local_G  # Return both the positions and the graph

def adjust_coordinates(coordinates, result_window):
    adjust_window = tk.Toplevel(result_window)
    adjust_window.title("Adjust Node Coordinates")
    adjust_window.geometry("500x700")

    text_widget = tk.Text(adjust_window, font=("Arial", 12), wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)

    for node, coord in coordinates.items():
        text_widget.insert(tk.END, f"{node}: {coord[0]:.4f}, {coord[1]:.4f}\n")

    instruction_label = tk.Label(adjust_window, text="Edit coordinates above, then click 'Apply Changes'")
    instruction_label.pack(pady=5)

    def apply_changes():
        new_coordinates = {}
        lines = text_widget.get("1.0", tk.END).split('\n')
        for line in lines:
            if line.strip():
                node, coords = line.split(':')
                x, y = map(float, coords.split(','))
                new_coordinates[node.strip()] = (x, y)
        adjust_window.destroy()
        update_plot(new_coordinates)

    apply_button = tk.Button(adjust_window, text="Apply Changes", command=apply_changes)
    apply_button.pack(pady=10)

def update_plot(new_coordinates):
    global node_coordinates_2d, local_G, nodes, all_nearest_nodes
    node_coordinates_2d = new_coordinates
    pos, updated_local_G = plot_combined_local_graph_2D(nodes, list(all_nearest_nodes), layout_type='custom', layout_params={'pos': new_coordinates}, skip_crossing_checks=True)
    
    # If you need to update the global local_G
    local_G = updated_local_G

def plot_combined_local_graph_3D(center_nodes, nearest_nodes):
    local_G = plot_combined_local_graph(center_nodes, nearest_nodes)
    
    # Get the spring layout in 3D
    pos = nx.spring_layout(local_G, dim=3)
    
    # Extract 3D coordinates for nodes
    node_x = [pos[node][0] for node in local_G.nodes()]
    node_y = [pos[node][1] for node in local_G.nodes()]
    node_z = [pos[node][2] for node in local_G.nodes()]
    
    # Create the 3D scatter plot for nodes
    node_trace = go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers+text',
        marker=dict(
            size=[5 + 5 * local_G.degree(node) for node in local_G.nodes()],
            color=['#d97706' if node in center_nodes else 'thistle' for node in local_G.nodes()],
            opacity=0.8,
        ),
        text=list(local_G.nodes()),
        hoverinfo='text',
        textposition="top center"
    )
    
    # Create the 3D plot for edges
    edge_x = []
    edge_y = []
    edge_z = []
    edge_text_x = []
    edge_text_y = []
    edge_text_z = []
    edge_texts = []

    edge_weights = [local_G[u][v]['weight'] for u, v in local_G.edges()]

    for (u, v), weight in zip(local_G.edges(), edge_weights):
        x0, y0, z0 = pos[u]
        x1, y1, z1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])
        
        # Calculate the midpoint of the edge
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        mid_z = (z0 + z1) / 2
        edge_text_x.append(mid_x)
        edge_text_y.append(mid_y)
        edge_text_z.append(mid_z)
        edge_texts.append(f'{weight:.2f}')
    
    edge_trace = go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(width=10, color='skyblue'),
        hoverinfo='none'
    )

    edge_text_trace = go.Scatter3d(
        x=edge_text_x, y=edge_text_y, z=edge_text_z,
        mode='text',
        text=edge_texts,
        textposition='middle center',
        hoverinfo='none',
        textfont=dict(color='steelblue', size=12)
    )
    
    # Set up the figure with nodes and edges
    fig = go.Figure(data=[edge_trace, node_trace, edge_text_trace],
                    layout=go.Layout(
                        title=f'3D Combined Local Graph for {", ".join(center_nodes)}',
                        showlegend=False,
                        margin=dict(b=20, l=5, r=5, t=40),
                        scene=dict(
                            xaxis=dict(showbackground=False),
                            yaxis=dict(showbackground=False),
                            zaxis=dict(showbackground=False),
                        )
                    ))

    # Show the 3D plot
    pio.show(fig)

def find_and_plot_multiple_nodes(root):
    global nodes, all_nearest_nodes, node_coordinates_2d, local_G
    G = get_graph_from_db()
    
    # Input 5 nodes in one line (comma-separated)
    node_input = simpledialog.askstring("Input", "Enter 5 nodes to compare (comma-separated):")
    
    if not node_input:
        messagebox.showerror("Error", "No input provided.")
        return
    
    # Split the input into a list of node names and remove any extra spaces
    nodes = [node.strip() for node in node_input.split(',')]
    
    # Check if exactly 5 nodes were provided
    if len(nodes) != 5:
        messagebox.showerror("Error", "Please enter exactly 5 nodes.")
        return
    
    # Check if all nodes exist in the graph
    for node in nodes:
        if node not in G.nodes():
            messagebox.showerror("Error", f"Node '{node}' not found in the graph.")
            return
    
    # Find nearest nodes for each input node
    all_nearest_nodes = set()
    result_text = ""
    for node in nodes:
        distances = nx.single_source_dijkstra_path_length(G, node)
        nearest_nodes = nsmallest(21, distances.items(), key=lambda x: x[1])[1:21]  # Get top 20 excluding the node itself
        all_nearest_nodes.update(nearest_nodes)
        
        result_text += f"\nTop 20 nearest nodes to {node}:\n"
        result_text += "\n".join([f"{i+1}. {n[0]}: {n[1]}" for i, n in enumerate(nearest_nodes)])
        result_text += "\n"
    
    # Create the result window
    result_window = tk.Toplevel(root)
    result_window.title("Nearest Nodes Results")
    result_window.geometry("600x900")
    
    # Display results
    text_widget = tk.Text(result_window, font=("Lato", 12), wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    text_widget.insert(tk.END, result_text)
    text_widget.config(state=tk.DISABLED)
    
    # Calculate the metrics for the selected nodes
    # df = calculate_node_metrics(G, nodes)

    # Display the table in the GUI
    # display_metrics(df)

    # Function to plot 2D graph and show coordinates
    def plot_2d_and_show_coords():
        global node_coordinates_2d, local_G
        node_coordinates_2d, local_G = plot_combined_local_graph_2D(nodes, list(all_nearest_nodes), 'spring_grid', {'k': 0.7, 'iterations': 50})
        
        # Create buttons for showing coordinates and adjusting them
        show_coords_button = tk.Button(button_frame, text="Show 2D Coordinates", 
                                       command=lambda: show_2d_coordinates(node_coordinates_2d))
        show_coords_button.pack(side=tk.LEFT, padx=5)

        adjust_coords_button = tk.Button(button_frame, text="Adjust Coordinates", 
                                         command=lambda: adjust_coordinates(node_coordinates_2d, result_window))
        adjust_coords_button.pack(side=tk.LEFT, padx=5)

    # Function to show 2D coordinates
    def show_2d_coordinates(coordinates):
        coord_window = tk.Toplevel(result_window)
        coord_window.title("2D Node Coordinates")
        coord_window.geometry("450x700")
        
        text_widget = tk.Text(coord_window, font=("Arial", 12), wrap=tk.WORD)
        text_widget.pack(expand=True, fill='both', padx=10, pady=10)
        
        for node, coord in coordinates.items():
            text_widget.insert(tk.END, f"{node}: ({coord[0]:.4f}, {coord[1]:.4f})\n")
        
        text_widget.config(state=tk.DISABLED)

    # Create buttons for different actions
    button_frame = tk.Frame(result_window)
    button_frame.pack(pady=10)

    plot_2d_button = tk.Button(button_frame, text="Plot 2D Graph", command=plot_2d_and_show_coords)
    plot_2d_button.pack(side=tk.LEFT, padx=5)

    plot_3d_button = tk.Button(button_frame, text="Plot 3D Graph", 
                               command=lambda: plot_combined_local_graph_3D(nodes, list(all_nearest_nodes)))
    plot_3d_button.pack(side=tk.LEFT, padx=5)

    # Update the window to ensure all widgets are drawn
    result_window.update()

def show_coordinates(node_coordinates):
    coord_window = tk.Toplevel()
    coord_window.title("Node Coordinates")
    coord_window.geometry("400x300")
    
    text_widget = tk.Text(coord_window, font=("Arial", 12), wrap=tk.WORD)
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    
    for node, coord in node_coordinates:
        text_widget.insert(tk.END, f"{node}: {coord}\n")
    
    text_widget.config(state=tk.DISABLED)