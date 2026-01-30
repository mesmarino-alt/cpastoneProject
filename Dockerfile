# Use an official PyTorch CPU image so the torch wheel is already present
FROM pytorch/pytorch:2.9.1-cpu

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Install system dependencies for common DB drivers and build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Railway provides PORT env var at runtime
EXPOSE 8000

# Use a shell command so the $PORT environment variable is expanded at runtime.
# Provide a default port (8000) if PORT is not set.
CMD ["sh", "-c", "gunicorn wsgi:app -b 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120"]
