import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
