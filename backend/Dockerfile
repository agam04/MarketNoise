FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps: gcc + libpq for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
# CPU-only torch keeps the image ~400 MB instead of 2 GB
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect Django static files into /app/staticfiles
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# 1 worker for t2/t3.micro (1 GB RAM); bump to 2+ on larger instances
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
