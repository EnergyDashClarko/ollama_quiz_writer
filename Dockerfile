# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r quizbot && useradd -r -g quizbot quizbot

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed in future)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY config.json .

# Create directories for data and logs
RUN mkdir -p quizzes logs && \
    chown -R quizbot:quizbot /app

# Copy default quiz files
COPY quizzes/ ./quizzes/

# Switch to non-root user
USER quizbot

# Expose port (not strictly necessary for Discord bot, but good practice)
EXPOSE 8080

# Health check (optional - checks if bot process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python.*main.py" > /dev/null || exit 1

# Set entrypoint
ENTRYPOINT ["python", "main.py"]