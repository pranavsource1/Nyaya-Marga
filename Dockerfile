FROM python:3.11-slim

# Create a non-root user to run the app on Hugging Face Spaces
RUN useradd -m -u 1000 user

WORKDIR /app

# Install system dependencies AND Redis
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Copy application and set ownership
COPY --chown=user:user . .

# Set permissions for upload directory
RUN mkdir -p /tmp/nyaya_uploads && chown -R user:user /tmp/nyaya_uploads

# Switch to the non-root user
USER user

# Ensure the start script is executable
RUN chmod +x start.sh

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Run the startup script (starts Redis, Celery, and Uvicorn)
CMD ["./start.sh"]
