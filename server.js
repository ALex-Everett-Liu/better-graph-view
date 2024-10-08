const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bodyParser = require('body-parser');
const path = require('path');
const PriorityQueue = require('priorityqueuejs'); // const PriorityQueue = require('./priorityQueue');
const Graph = require('graphology');
const forceAtlas2 = require('graphology-layout-forceatlas2');
// const { createCanvas } = require('canvas');

const app = express();
const port = process.env.PORT || 3001;
// const port = 3001;

// Assuming DB_PATH is the path to your SQLite database
const DB_PATH = './graph_data.db';

app.use(express.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(express.static('public'));
app.use(express.json());

function getGraphFromDB(callback) {
    const db = new sqlite3.Database(DB_PATH);
    db.all("SELECT * FROM edges", (err, rows) => {
        db.close();
        if (err) {
            callback(err, null);
        } else {
            callback(null, rows);
        }
    });
}

function getRelatedChunks(dbName, startChunk, maxDepth = 3) {
    return new Promise((resolve, reject) => {
        const db = new sqlite3.Database(dbName, (err) => {
            if (err) {
                reject(err);
                return;
            }

            const related = new Map();
            const queue = [[startChunk, 0]];
            const visited = new Set();

            function processDepth(depth) {
                if (depth >= maxDepth || queue.length === 0) {
                    db.close();
                    resolve(related);
                    return;
                }

                const newQueue = [];
                let processed = 0;

                queue.forEach(([current, currentWeight]) => {
                    if (current !== startChunk) {
                        related.set(current, Math.max(related.get(current) || 0, currentWeight));
                    }

                    db.all('SELECT target, weight FROM edges WHERE source = ?', [current], (err, rows) => {
                        if (err) {
                            reject(err);
                            return;
                        }

                        rows.forEach(({ target, weight }) => {
                            if (!visited.has(target)) {
                                newQueue.push([target, weight]);
                                visited.add(target);
                            }
                        });

                        processed++;
                        if (processed === queue.length) {
                            queue.length = 0;
                            queue.push(...newQueue);
                            processDepth(depth + 1);
                        }
                    });
                });
            }

            processDepth(0);
        });
    });
}

function sortRelatedChunks(related) {
    return Array.from(related.entries())
        .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]));
}

function dijkstra(graph, start) {
    const distances = {};
    const pq = new PriorityQueue((a, b) => b[1] - a[1]);
    
    graph.forEach(edge => {
        distances[edge.source] = Infinity;
        distances[edge.target] = Infinity;
    });
    
    distances[start] = 0;
    pq.enq([start, 0]);
    
    while (!pq.isEmpty()) {
        const [node, dist] = pq.deq();
        
        if (dist > distances[node]) continue;
        
        graph.forEach(edge => {
            if (edge.source === node) {
                const newDist = dist + edge.weight;
                if (newDist < distances[edge.target]) {
                    distances[edge.target] = newDist;
                    pq.enq([edge.target, newDist]);
                }
            }
        });
    }
    
    return distances;
}

function calculateNodeMetrics(graph, centerNodes) {
    const results = centerNodes.map(node => {
        const distances = dijkstra(graph, node);
        const sortedDistances = Object.entries(distances)
            .filter(([n]) => n !== node)
            .sort((a, b) => a[1] - b[1]);
        
        const connectedNodes = graph.filter(edge => edge.source === node || edge.target === node).length / 2;
        const avgDist5 = sortedDistances.slice(0, 5).reduce((sum, [, dist]) => sum + dist, 0) / Math.min(5, sortedDistances.length);
        const avgDist10 = sortedDistances.slice(0, 10).reduce((sum, [, dist]) => sum + dist, 0) / Math.min(10, sortedDistances.length);
        const avgDist20 = sortedDistances.slice(0, 20).reduce((sum, [, dist]) => sum + dist, 0) / Math.min(20, sortedDistances.length);
        
        return {
            Node: node,
            ConnectedNodes: connectedNodes,
            Distance5: avgDist5,
            Distance10: avgDist10,
            Distance20: avgDist20
        };
    });
    
    return results;
}

function calculateEdgeStatistics(graph) {
    const weights = graph.map(edge => edge.weight);
    const average = weights.reduce((sum, weight) => sum + weight, 0) / weights.length;
    const median = weights.sort((a, b) => a - b)[Math.floor(weights.length / 2)];
    
    return { average, median };
}

function plotCombinedLocalGraph(centerNodes, nearestNodes, callback) {
    getGraphFromDB((err, edges) => {
        if (err) {
            callback(err, null);
            return;
        }

        const G = new Graph();

        // Add all nodes and edges
        edges.forEach(edge => {
            if (!G.hasNode(edge.source)) G.addNode(edge.source);
            if (!G.hasNode(edge.target)) G.addNode(edge.target);
            G.addEdge(edge.source, edge.target, { weight: edge.weight });
        });

        const localG = new Graph();

        // Add center nodes and nearest nodes
        centerNodes.forEach(node => localG.addNode(node));
        nearestNodes.forEach(([node]) => localG.addNode(node));

        // Add edges
        centerNodes.forEach(centerNode => {
            nearestNodes.forEach(([node]) => {
                if (G.hasEdge(centerNode, node)) {
                    localG.addEdge(centerNode, node, { weight: G.getEdgeAttribute(centerNode, node, 'weight') });
                }
            });
        });

        nearestNodes.forEach(([node]) => {
            G.forEachNeighbor(node, (neighbor) => {
                if (localG.hasNode(neighbor)) {
                    localG.addEdge(node, neighbor, { weight: G.getEdgeAttribute(node, neighbor, 'weight') });
                }
            });
        });

        // Layout
        const positions = forceAtlas2(localG, { iterations: 50, settings: { scalingRatio: 10 } });

        // Draw
        const canvas = createCanvas(800, 600);
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, 800, 600);

        // Draw edges
        ctx.strokeStyle = 'skyblue';
        localG.forEachEdge((edge, attributes, source, target) => {
            const sourcePos = positions[source];
            const targetPos = positions[target];
            ctx.beginPath();
            ctx.moveTo(sourcePos.x, sourcePos.y);
            ctx.lineTo(targetPos.x, targetPos.y);
            ctx.stroke();

            // Draw edge weight
            const midX = (sourcePos.x + targetPos.x) / 2;
            const midY = (sourcePos.y + targetPos.y) / 2;
            ctx.fillStyle = 'steelblue';
            ctx.font = '8px Arial';
            ctx.fillText(attributes.weight.toFixed(2), midX, midY);
        });

        // Draw nodes
        localG.forEachNode((node, attributes) => {
            const pos = positions[node];
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 5, 0, 2 * Math.PI);
            ctx.fillStyle = centerNodes.includes(node) ? '#d97706' : 'thistle';
            ctx.fill();

            // Draw node label
            ctx.fillStyle = 'black';
            ctx.font = '11px Arial';
            ctx.fillText(node, pos.x + 6, pos.y + 6);
        });

        callback(null, canvas.toBuffer());
    });
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.post('/related-chunks', (req, res) => {
    const startChunk = req.body.startChunk;
    const dbName = path.join(__dirname, 'graph_data.db');

    getRelatedChunks(dbName, startChunk)
        .then(related => {
            const sortedRelated = sortRelatedChunks(related);
            res.json(sortedRelated);
        })
        .catch(err => {
            console.error("Error:", err);
            res.status(500).json({ error: 'An error occurred while processing your request.' });
        });
});

// New endpoint for keyword search
app.post('/search', (req, res) => {
    const keyword = req.body.keyword;
    const dbName = path.join(__dirname, 'graph_data.db');

    const db = new sqlite3.Database(dbName, (err) => {
        if (err) {
            console.error(err.message);
            res.status(500).json({ error: 'Failed to connect to the database' });
            return;
        }

        // Search in both source and target columns of the edges table
        const query = `
            SELECT DISTINCT source AS chunk FROM edges WHERE source LIKE ?
            UNION
            SELECT DISTINCT target AS chunk FROM edges WHERE target LIKE ?
        `;
        const searchTerm = `%${keyword}%`;

        db.all(query, [searchTerm, searchTerm], (err, rows) => {
            if (err) {
                console.error(err.message);
                res.status(500).json({ error: 'An error occurred while searching the database' });
            } else {
                res.json(rows.map(row => row.chunk));
            }
            db.close();
        });
    });
});

app.post('/add-node-and-edges', (req, res) => {
    const nodesInput = req.body.nodesInput;

    if (!nodesInput) {
        return res.status(400).send('Input is required.');
    }

    const db = new sqlite3.Database(DB_PATH);

    db.serialize(() => {
        const edgeSet = new Set();  // To keep track of inserted edges

        nodesInput.split('\n').forEach(line => {
            line = line.trim();
            if (!line) return;

            try {
                let [nodeName, relations] = line.split(':');
                nodeName = nodeName.trim();
                relations = relations.trim();
                const relatedNodes = relations.split(',').map(x => x.trim());

                db.run("INSERT OR IGNORE INTO nodes (name) VALUES (?)", [nodeName]);

                for (let i = 0; i < relatedNodes.length; i += 2) {
                    const relatedNode = relatedNodes[i];
                    const weight = parseFloat(relatedNodes[i + 1]);

                    if (isNaN(weight)) {
                        throw new Error(`Invalid weight for related node: ${relatedNodes[i + 1]}`);
                    }

                    db.run("INSERT OR IGNORE INTO nodes (name) VALUES (?)", [relatedNode]);

                    // Insert the edge with its weight
                    db.run("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)", [nodeName, relatedNode, weight]);

                    // Check if reverse edge is already in the input or in the set
                    if (!edgeSet.has(`${relatedNode}:${nodeName}`)) {
                        db.run("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)", [relatedNode, nodeName, weight]);
                    }

                    // Mark this edge as processed
                    edgeSet.add(`${nodeName}:${relatedNode}`);
                }
            } catch (err) {
                return res.status(400).send(`Error processing line: ${line}. Error: ${err.message}`);
            }
        });

        res.send('Node and edges added successfully!');
    });

    db.close();
});

app.post('/nearest-nodes', (req, res) => {
    const { node, n } = req.body;
    getGraphFromDB((err, graph) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }

        const distances = dijkstra(graph, node);
        
        // Sort distances and filter out unreachable nodes
        const sortedDistances = Object.entries(distances)
            .filter(([, distance]) => distance !== Infinity)
            .sort((a, b) => a[1] - b[1]);

        // Return all reachable nodes, up to n
        const nearestNodes = sortedDistances.slice(0, n);
        
        res.json(nearestNodes);
    });
});

app.post('/combined-graph', (req, res) => {
    const { nodes } = req.body;
    if (!nodes || nodes.length !== 5) {
        return res.status(400).json({ error: 'Please provide exactly 5 nodes.' });
    }

    getGraphFromDB((err, edges) => {
        if (err) {
            return res.status(500).json({ error: 'Database error' });
        }

        const G = new Graph();

        // Add all nodes and edges
        edges.forEach(edge => {
            if (!G.hasNode(edge.source)) G.addNode(edge.source);
            if (!G.hasNode(edge.target)) G.addNode(edge.target);
            G.addEdge(edge.source, edge.target, { weight: edge.weight });
        });

        const subgraph = new Graph();
        const addedNodes = new Set();

        // Add the 5 given nodes and their nearest neighbors
        nodes.forEach(node => {
            if (G.hasNode(node)) {
                subgraph.addNode(node);
                addedNodes.add(node);

                G.forEachNeighbor(node, (neighbor, attributes) => {
                    if (!addedNodes.has(neighbor)) {
                        subgraph.addNode(neighbor);
                        addedNodes.add(neighbor);
                    }
                    subgraph.addEdge(node, neighbor, attributes);
                });
            }
        });

        // Convert subgraph to JSON format suitable for D3
        const graphData = {
            nodes: Array.from(addedNodes).map(node => ({ id: node })),
            links: subgraph.edges().map(edge => ({
                source: subgraph.source(edge),
                target: subgraph.target(edge),
                weight: subgraph.getEdgeAttribute(edge, 'weight')
            }))
        };

        res.json(graphData);
    });
});

// function findNearestNodes(graph, startNode, n = 30) {
    // const distances = dijkstra(graph, startNode);
    // return Object.entries(distances)
        // .filter(([node]) => node !== startNode)
        // .sort((a, b) => a[1] - b[1])
        // .slice(0, n);
// }

app.post('/node-metrics', (req, res) => {
    const { nodes } = req.body;
    getGraphFromDB((err, graph) => {
        if (err) {
            return res.status(500).json({ error: 'Error reading from database' });
        }
        const metrics = calculateNodeMetrics(graph, nodes);
        res.json(metrics);
    });
});

app.get('/edge-statistics', (req, res) => {
    getGraphFromDB((err, graph) => {
        if (err) {
            return res.status(500).json({ error: 'Error reading from database' });
        }
        const statistics = calculateEdgeStatistics(graph);
        res.json(statistics);
    });
});

app.get('/nearest-nodes.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'nearest-nodes.html'));
});

app.get('/node-metrics.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'node-metrics.html'));
});

app.get('/edge-statistics.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'edge-statistics.html'));
});



app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});

// app.listen(3000, () => console.log('Server running on port 3000'));

module.exports = app;
