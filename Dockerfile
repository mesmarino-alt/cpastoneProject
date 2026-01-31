# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir numpy==2.3.5 \
    && python -m pip install --no-cache-dir Flask==3.1.2 Flask-Bcrypt==1.0.1 Flask-Login==0.6.3 PyMySQL==1.1.2 \
    && python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.9.1+cpu" \
    && python -m pip install --no-cache-dir sentence-transformers==5.1.2 \
    && grep -v '^torch' requirements.txt > reqs_no_torch.txt \
    && python -m pip install --no-cache-dir -r reqs_no_torch.txt \
    && python -m pip install --no-cache-dir gunicorn==23.0.0 \
    # Verify critical packages are importable and print versions to build logs
    && python -c "import numpy as np; print('numpy==%s' % np.__version__)" \
    && python -c "import flask; import sys; print('flask==%s' % flask.__version__)" \
    && python -c "import flask_bcrypt; print('flask_bcrypt OK')" \
    && python -c "import pymysql; print('pymysql OK')" \
    && python -c "import sentence_transformers; print('sentence_transformers OK')" \
    && python -c "import torch; print('torch==%s' % torch.__version__)" \
    # Print installed packages for debugging
    && python -m pip freeze | sed -n '1,200p'

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Run the web service on container startup.
CMD ["gunicorn", "-b", ":8080", "main:app"]