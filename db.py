import os
from urllib.parse import urlparse
import pymysql.cursors

_SCHEMA_INITIALIZED = False

def _parse_database_url(url: str):
    p = urlparse(url)
    return {
        'host': p.hostname or 'localhost',
        'port': p.port or 3306,
        'user': p.username or '',
        'password': p.password or '',
        'database': (p.path.lstrip('/') or ''),
    }

def get_db():
    """Return a pymysql connection.

    Reads DATABASE_URL (preferred) or DB_HOST/DB_USER/DB_PASS/DB_NAME/DB_PORT.
    Raises RuntimeError with a clear message on failure so logs show actionable info.
    """
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        cfg = _parse_database_url(db_url)
    else:
        cfg = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASS', ''),
            'database': os.getenv('DB_NAME', 'cap_finditfast'),
        }

    try:
        conn = pymysql.connect(
            host=cfg['host'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database'],
            port=cfg['port'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        _ensure_schema(conn)
        return conn
    except Exception as e:
        # Raise a clearer runtime error so Railway logs show the cause
        raise RuntimeError(f"Database connection failed to {cfg['host']}:{cfg['port']} (db='{cfg.get('database')}'): {e}") from e

def _ensure_schema(conn):
    """Run schema.sql once per process to create missing tables."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        _SCHEMA_INITIALIZED = True
        return
    try:
        with open(schema_path, 'r') as f:
            sql = f.read()
        # Execute each statement individually
        with conn.cursor() as cur:
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)
        conn.commit()
        print("[DB] Schema initialized successfully.")
    except Exception as e:
        print(f"[DB] Warning: schema initialization error (tables may already exist): {e}")
    _SCHEMA_INITIALIZED = True
