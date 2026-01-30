# One ROM Sales tracking - (Public) Reader Service

from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import signal
import sys

app = Flask(__name__)
CORS(app)
# To restrict CORS to specific origins, uncomment the line below and adjust as needed
# CORS(app, origins=['https://piers.rocks', 'https://onerom.org'])

DB_PATH = 'file:/data/sales.db?mode=ro'

@app.route('/api/sales/total')
def total_sales():
    conn = sqlite3.connect(DB_PATH, uri=True)
    result = conn.execute('SELECT SUM(quantity) FROM sales').fetchone()
    conn.close()
    return jsonify({'total': result[0] or 0})

@app.route('/api/sales/by-type')
def sales_by_type():
    conn = sqlite3.connect(DB_PATH, uri=True)
    results = conn.execute('''
        SELECT model, variant, SUM(quantity) as count 
        FROM sales 
        GROUP BY model, variant
    ''').fetchall()
    conn.close()
    
    breakdown = [{'model': r[0], 'variant': r[1], 'count': r[2]} for r in results]
    return jsonify({'breakdown': breakdown})

def shutdown_handler(sig, frame):
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, shutdown_handler)
    app.run(host='0.0.0.0', port=5000)