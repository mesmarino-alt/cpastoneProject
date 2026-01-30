# Use a slim Python base and install PyTorch CPU wheel from the official PyTorch index
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Install system dependencies for common DB drivers and build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install PyTorch CPU wheel first from the PyTorch index,
# then install the rest of the requirements. This avoids relying on a non-existent
# pytorch/pytorch:... tag on Docker Hub.
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir Flask==3.1.2 \
    && python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.9.1+cpu" \
    && grep -v '^torch' requirements.txt > reqs_no_torch.txt \
    && python -m pip install --no-cache-dir -r reqs_no_torch.txt \
    && python -m pip install --no-cache-dir gunicorn==23.0.0 \
    # Verify critical packages are importable and print versions to build logs
    && python -c "import flask; import sys; print('flask==%s' % flask.__version__)" \
    && python -c "import torch; print('torch==%s' % torch.__version__)"

# Copy app
COPY . .

# Railway provides PORT env var at runtime
EXPOSE 8000

# Use a shell command so the $PORT environment variable is expanded at runtime.
# Provide a default port (8000) if PORT is not set. Use python -m gunicorn to avoid
# relying on an executable being present in PATH.
CMD ["sh", "-c", "python -m gunicorn wsgi:app -b 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120"]
