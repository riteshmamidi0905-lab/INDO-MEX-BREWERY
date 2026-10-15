# NASHA Enterprise AI Lab: minimal image for the API (SYNTHETIC DATA / NOT PRODUCTION DEPLOYED). Build context = repository root.
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY lab/requirements.txt lab/requirements.txt
RUN pip install --no-cache-dir -r lab/requirements.txt
COPY . .
RUN mkdir /data && chown 10001 /data
ENV PYTHONPATH=/app/lab PYTHONDONTWRITEBYTECODE=1
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "--factory", "nasha_lab.serve:app", "--host", "0.0.0.0", "--port", "8000"]
