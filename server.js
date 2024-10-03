const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 3001;

// Assuming DB_PATH is the path to your SQLite database
const DB_PATH = './graph_data.db';

app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

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

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
