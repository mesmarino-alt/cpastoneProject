# WSGI entrypoint for production servers
# Expose `app` for WSGI servers like Gunicorn
try:
    from app import app
except Exception as e:
    # Fail with a clear error so hosting logs show the problem
    raise ImportError("Cannot import 'app' from app.py. Ensure your Flask app is defined as `app` in app.py") from e
