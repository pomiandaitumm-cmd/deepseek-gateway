FROM python:3.11-slim

WORKDIR /app

# Create data directory (database volume mount point)
RUN mkdir -p /app/data

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY create_key.py disable_key.py usage_report.py add_quota.py set_quota.py ./

# Expose port
EXPOSE 8000

# Start
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]