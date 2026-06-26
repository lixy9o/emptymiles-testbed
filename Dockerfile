# Container image for the EmptyMiles matching testbed API.
# Build:  docker build -t emptymiles-api .
# Run:    docker run -p 8000:8000 emptymiles-api   then open http://localhost:8000/docs
FROM python:3.12-slim

WORKDIR /app

# Install deps first so the layer caches across code changes.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Only what the API needs at runtime (no dashboard, tests, or docs).
COPY src ./src
COPY api.py .

# Honour the platform's $PORT (Render, Fly, Cloud Run inject it); default 8000 locally.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
