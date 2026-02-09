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

    # Seed admin account if none exists
    _seed_admin(conn)

    _SCHEMA_INITIALIZED = True

def _seed_admin(conn):
    """Create a default admin user if no admin account exists in the database.

    Configure via environment variables (set these in Railway):
        ADMIN_NAME        – display name       (default: Admin)
        ADMIN_STUDENT_ID  – student/employee ID (default: ADMIN-001)
        ADMIN_EMAIL       – login email         (default: admin@finditfast.com)
        ADMIN_PASSWORD    – login password      (default: admin123)

    ⚠️  Change ADMIN_PASSWORD in Railway env vars before going live!
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
            if cur.fetchone():
                return  # admin already exists

        # Import bcrypt here to avoid circular imports
        from flask_bcrypt import generate_password_hash

        name       = os.getenv('ADMIN_NAME', 'Admin')
        student_id = os.getenv('ADMIN_STUDENT_ID', 'ADMIN-001')
        email      = os.getenv('ADMIN_EMAIL', 'admin@finditfast.com')
        password   = os.getenv('ADMIN_PASSWORD', 'admin123')

        pw_hash = generate_password_hash(password).decode('utf-8')

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, student_id, email, password_hash, role, active, created_at)
                VALUES (%s, %s, %s, %s, 'admin', 1, NOW())
            """, (name, student_id, email, pw_hash))
        conn.commit()
        print(f"[DB] ✓ Default admin account created: {email}")
    except Exception as e:
        print(f"[DB] Warning: could not seed admin account: {e}")
