# Minimal Dockerfile for Flask app
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Install system dependencies for common DB drivers and build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
# Install PyTorch CPU wheel from the official PyTorch index first so
# the `torch==2.9.1+cpu` artifact (which lives on the PyTorch index) can be found,
# then install the rest of the requirements.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.9.1+cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Railway provides PORT env var at runtime
EXPOSE 8000
CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:$PORT", "--workers", "4", "--timeout", "120"]
