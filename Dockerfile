FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with verbose output
RUN pip install --upgrade pip && \
    pip install wheel && \
    pip install --no-cache-dir -r requirements.txt -v

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "web_server:app", "--host", "0.0.0.0", "--port", "8000"]