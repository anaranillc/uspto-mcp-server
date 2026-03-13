FROM python:3.12-slim

# Ensure Python output is sent straight to stdout/stderr without buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Run as non-root user for security
RUN useradd --create-home appuser
USER appuser

# The MCP server communicates over stdio
ENTRYPOINT ["python", "server.py"]
