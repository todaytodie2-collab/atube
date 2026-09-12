# A TuBe Ultra-Fast Media Platform Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Persistent storage directories
VOLUME ["/app/config", "/app/data"]

EXPOSE 8085

ENV PYTHONUNBUFFERED=1
ENV PORT=8085

CMD ["python", "server.py", "8085"]
