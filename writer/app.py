# One ROM Sales tracking - Writer/Admin Service

from flask import Flask, jsonify, request, render_template
import sqlite3
from datetime import datetime
import signal
import sys
import logging

SKU_MAP = {
    'fire24': {'model': 'Fire', 'variant': '24pin'},
    'fire28': {'model': 'Fire', 'variant': '28pin'},
    'ice24': {'model': 'Ice', 'variant': '24pin'},
    'ice28': {'model': 'Ice', 'variant': '28pin'},
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_PATH_RO = 'file:/data/sales.db?mode=ro'
DB_PATH_WR = 'file:/data/sales.db?mode=rwc'

def init_db():
    conn = sqlite3.connect(DB_PATH_WR, uri=True)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            variant TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            seller TEXT DEFAULT 'piers.rocks',
            notes TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sales/recent')
def recent_sales():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    conn = sqlite3.connect(DB_PATH_RO, uri=True)
    results = conn.execute('''
        SELECT id, date_added, model, variant, quantity, seller, notes
        FROM sales 
        ORDER BY date_added DESC 
        LIMIT ? OFFSET ?
    ''', (limit, offset)).fetchall()
    
    total_count = conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0]
    conn.close()
    
    entries = [{
        'id': r[0],
        'date': r[1],
        'model': r[2],
        'variant': r[3],
        'quantity': r[4],
        'seller': r[5],
        'notes': r[6]
    } for r in results]
    return jsonify({'entries': entries, 'total_count': total_count})

def insert_sale(model, variant, quantity, seller, notes=''):
    conn = sqlite3.connect(DB_PATH_WR, uri=True)
    conn.execute(
        'INSERT INTO sales (model, variant, quantity, seller, notes) VALUES (?, ?, ?, ?, ?)',
        (model, variant, quantity, seller, notes)
    )
    conn.commit()
    conn.close()

@app.route('/api/sales', methods=['POST'])
def add_sale():
    data = request.json
    insert_sale(data['model'], data['variant'], data.get('quantity', 1), data.get('seller', 'piers.rocks'), data.get('notes', ''))
    return jsonify({'status': 'ok'})

@app.route('/api/sales/<int:sale_id>', methods=['DELETE'])
def delete_sale(sale_id):
    conn = sqlite3.connect(DB_PATH_WR, uri=True)
    conn.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/sales/<int:sale_id>', methods=['PUT'])
def update_sale(sale_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH_WR, uri=True)
    conn.execute(
        'UPDATE sales SET model = ?, variant = ?, quantity = ?, seller = ?, notes = ? WHERE id = ?',
        (data['model'], data['variant'], data['quantity'], data['seller'], data.get('notes', ''), sale_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

def match_sku(sku):
    """Match SKU case-insensitively by prefix"""
    sku_upper = sku.upper()
    for prefix, mapping in SKU_MAP.items():
        if sku_upper.startswith(prefix.upper()):
            return mapping
    return None

@app.route('/api/woocommerce/webhook', methods=['POST'])
def woocommerce_webhook():
    try:
        # Log all incoming requests
        logger.info(f"Webhook request - Content-Type: {request.content_type}, Headers: {dict(request.headers)}")

        # Handle requests without JSON gracefully
        if request.content_type != 'application/json':
            logger.warning(f"Non-JSON request - Content-Type: {request.content_type}, Raw data: {request.data}")
            return jsonify({'status': 'ok', 'message': 'non-json request ignored'}), 200

        data = request.json
        logger.info(f"Received WooCommerce webhook: {data}")
        
        # Only process "processing" orders - i.e. paid but not yet completed
        order_status = data.get('status', '')
        if order_status != 'processing':
            logger.info(f"Skipping order with status: {order_status}")
            return jsonify({'status': 'ok', 'message': 'not processing'}), 200
        
        if not data:
            logger.error("Empty webhook payload")
            return jsonify({'status': 'error', 'message': 'empty payload'}), 400
        
        if 'line_items' not in data:
            logger.error(f"No line_items in payload: {data}")
            return jsonify({'status': 'error', 'message': 'no line items'}), 400
        
        processed = 0
        skipped = 0
        
        for item in data['line_items']:
            sku = item.get('sku', '')
            quantity = item.get('quantity', 1)
            product_name = item.get('name', 'unknown')
            
            logger.info(f"Processing item: SKU={sku}, qty={quantity}, name={product_name}")
            
            if not sku:
                logger.warning(f"Item has no SKU: {item}")
                skipped += 1
                continue
            
            mapping = match_sku(sku)
            if mapping:
                logger.info(f"Matched SKU {sku} -> {mapping['model']} {mapping['variant']}")
                insert_sale(mapping['model'], mapping['variant'], quantity, 'piers.rocks', f"packom.net Order: {data.get('id')}")
                processed += 1
            else:
                logger.warning(f"Unknown SKU: {sku} (item: {product_name})")
                skipped += 1
        
        logger.info(f"Webhook complete: {processed} items processed, {skipped} skipped")
        return jsonify({'status': 'ok', 'processed': processed, 'skipped': skipped})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def shutdown_handler(sig, frame):
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, shutdown_handler)
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)