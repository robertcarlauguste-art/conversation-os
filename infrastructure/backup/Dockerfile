FROM postgres:18
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/backup-venv \
    && /opt/backup-venv/bin/pip install --no-cache-dir boto3==1.40.33 cryptography==46.0.1 httpx==0.28.1
WORKDIR /backup
COPY backup.py recordings.py ./
USER postgres
ENTRYPOINT ["/opt/backup-venv/bin/python", "/backup/backup.py"]
