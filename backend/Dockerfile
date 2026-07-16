# Backend image — build context is the REPO ROOT (see docker-compose.yml) because the app loads
# schema/ and data/ by relative path (schema-driven pipeline, locked #5).
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY schema/ schema/
COPY data/ data/

# Provenance stamp (ADR-0002): pass --build-arg GIT_SHA=$(git rev-parse --short HEAD) to bake the commit.
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
