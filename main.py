from database import initialize_database, DB_PATH
import tkinter as tk

def main():
    initialize_database()
    
    root = tk.Tk()
    root.title("Graph Builder")
    root.geometry("500x400")  # Set window size root.geometry("500x350")

    style = {
        'font': ('Montserrat', 15),
        'width': 25,
        'height': 2,
        'bg': '#2B7396',
        'fg': 'lightgreen',
    }
    
    add_button = tk.Button(root, text="Add Node and Edges", command=add_node_and_edges, **style)
    add_button.pack(pady=10)
    
    plot_button = tk.Button(root, text="Plot Graph", command=plot_graph, **style)
    plot_button.pack(pady=10)
    
    nearest_button = tk.Button(root, text="Find Nearest Nodes", command=find_nearest_nodes, **style)
    nearest_button.pack(pady=10)

    multiple_nodes_button = tk.Button(root, text="Compare 5 Nodes", command=lambda: find_and_plot_multiple_nodes(root), **style)
    multiple_nodes_button.pack(pady=10)

    # Remove the separate button for printing coordinates, as it's now part of plot_combined_local_graph_2D_and_3D

    stats_button = tk.Button(root, text="Calculate Edge Statistics", command=calculate_edge_statistics, **style)
    stats_button.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()
