const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const app = express();
const PORT = 3000;

// Assuming DB_PATH is the path to your SQLite database
const DB_PATH = './graph_data.db';

app.use(bodyParser.urlencoded({ extended: true }));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/add-node-and-edges', (req, res) => {
    const nodesInput = req.body.nodesInput;

    if (!nodesInput) {
        return res.status(400).send('Input is required.');
    }

    const db = new sqlite3.Database(DB_PATH);

    db.serialize(() => {
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
                    db.run("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)", [nodeName, relatedNode, weight]);
                    db.run("INSERT OR REPLACE INTO edges (source, target, weight) VALUES (?, ?, ?)", [relatedNode, nodeName, weight]);
                }
            } catch (err) {
                return res.status(400).send(`Error processing line: ${line}. Error: ${err.message}`);
            }
        });

        res.send('Node and edges added successfully!');
    });

    db.close();
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
