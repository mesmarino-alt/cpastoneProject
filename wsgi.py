# Robust WSGI entrypoint for production servers
# Expose `app` and `application` for WSGI servers like Gunicorn
import traceback

try:
    # Prefer a direct `app` variable from app.py
    from app import app
except Exception:
    # Print the full import traceback to build/runtime logs for debugging
    traceback.print_exc()
    # Try common patterns: app factory `create_app()` in app.py or package
    try:
        from app import create_app
        app = create_app()
    except Exception:
        # Final fallback: re-raise the original failure so the container logs show it
        raise ImportError("Cannot import or create a Flask `app`. Ensure app.py defines `app` or a `create_app()` factory.")

# Also expose `application` for some WSGI servers
application = app
