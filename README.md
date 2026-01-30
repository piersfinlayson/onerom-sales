# One ROM Sales Tracker

Web service to track One ROM sales with public read-only API and internal admin interface.

The internal admin interface exposes a user-facing HTML page and a woocommerce web-hook to automatically log sales (when an order reaches "processing" status).

## Setup

```bash
sudo useradd --no-create-home --uid 10000 onerom
mkdir -p ./data
sudo chown onerom:onerom ./data
```

## Running

```bash
./restart.sh
```

Note that the writer service runs in debug mode, so HTML changes will be reload immediately.

Access:
- Reader API: http://server1:8106/api/sales/total
- Writer Admin: http://server1:8107/

## Architecture

- **Reader** (port 8106): Public read-only JSON API
- **Writer** (port 8107): Internal admin interface with HTML form
- **Database**: SQLite shared between both services

## Directory Structure
```
onerom-sales/
├── docker-compose.yml
├── data/
│   └── sales.db (created at runtime)
├── reader/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── writer/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py
    └── templates/
        └── index.html
```

## API Endpoints

### Reader (Public)
- `GET /api/sales/total` - Total sales count
- `GET /api/sales/by-type` - Breakdown by model/variant

### Writer (Internal)
- `GET /` - HTML admin interface
  - View total sales and breakdown by type
  - Add new sales entries
  - View, edit, and delete recent sales
- `GET /api/sales/recent?offset=0&limit=10` - Paginated sales entries (returns IDs for editing/deleting)
- `POST /api/sales` - Add new sale
  - Body: `{"model": "Fire", "variant": "28pin", "quantity": 1, "seller": "piers.rocks"}`
- `PUT /api/sales/<id>` - Update existing sale
  - Body: `{"model": "Fire", "variant": "28pin", "quantity": 2, "seller": "piers.rocks"}`
- `DELETE /api/sales/<id>` - Delete sale by ID
- `POST /api/woocommerce/webhook` - WooCommerce order webhook
  - Automatically processes completed orders and adds sales based on SKU
  - SKU mapping: fire24, fire28, ice24, ice28 (case-insensitive, prefix matching)

## Database Schema
```sql
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,           -- 'Ice', 'Fire'
    variant TEXT NOT NULL,         -- '24pin', '28pin'
    quantity INTEGER NOT NULL DEFAULT 1,
    seller TEXT DEFAULT 'piers.rocks',
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Backup

SQLite database is in `./data/sales.db`. Back up this file regularly.

## License

MIT License - see [LICENSE]() file for details.