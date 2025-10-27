FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Minimal base and up-to-date pip
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python -m pip install --no-cache-dir --upgrade pip

# Project bits used for packaging + runtime
COPY pyproject.toml poetry.lock* /app/
COPY README.md /app/README.md
COPY src /app/src
COPY rules /app/rules
COPY schemas /app/schemas
COPY vocab /app/vocab

# Install your CLI (provides `classify`)
RUN pip install --no-cache-dir .

COPY rules /usr/local/lib/python3.12/rules

# Default env so the CLI always finds the data (can be overridden by .env)
ENV RULES_PATH=/app/rules/rules.json \
    ULOG_RULES_PATH=/app/rules/rules.json \
    SCHEMAS_DIR=/app/schemas \
    ULOG_SCHEMAS_DIR=/app/schemas \
    VOCAB_PATH=/app/vocab/vocab.json \
    ULOG_VOCAB_PATH=/app/vocab/vocab.json

# Runner
COPY local_pipeline/classifier/app.py /app/app.py
VOLUME ["/in", "/out"]
ENTRYPOINT ["python", "/app/app.py"]
