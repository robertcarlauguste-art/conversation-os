import io

import backup
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def decrypt(data, key):
    header = data[: len(backup.MAGIC) + 12]
    decryptor = Cipher(
        algorithms.AES(key), modes.GCM(header[-12:], data[-16:])
    ).decryptor()
    decryptor.authenticate_additional_data(header)
    return decryptor.update(data[len(header) : -16]) + decryptor.finalize()


def test_encrypt_roundtrip_and_tamper(tmp_path):
    key = b"x" * 32
    source, destination = tmp_path / "source", tmp_path / "encrypted"
    source.write_bytes(b"synthetic tenant data" * 100000)
    backup.encrypt_file(source, destination, key)
    data = destination.read_bytes()
    assert decrypt(data, key) == source.read_bytes()
    damaged = bytearray(data)
    damaged[100] ^= 1
    with pytest.raises(InvalidTag):
        decrypt(bytes(damaged), key)
    with pytest.raises(InvalidTag):
        decrypt(data, b"y" * 32)


def test_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "MAX_BYTES", 4)
    source = tmp_path / "source"
    source.write_bytes(b"12345")
    with pytest.raises(ValueError, match="size limit"):
        backup.encrypt_file(source, tmp_path / "encrypted", b"x" * 32)


@pytest.mark.parametrize("payload", [b"changed", b"", b"too long payload"])
def test_remote_mismatch_rejected(payload):
    class Client:
        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(payload)}

    with pytest.raises(ValueError):
        backup.verify_remote(Client(), "private", "object", "bad-hash", 7)


def test_remote_roundtrip():
    class Client:
        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(b"abc")}

    backup.verify_remote(
        Client(), "private", "object", backup.hashlib.sha256(b"abc").hexdigest(), 3
    )


def test_failed_verification_never_signals_success(monkeypatch):
    values = {
        "BACKUP_ENDPOINT_URL": "https://storage.invalid",
        "BACKUP_ACCESS_KEY_ID": "id",
        "BACKUP_SECRET_ACCESS_KEY": "secret",
        "BACKUP_BUCKET": "backup-only",
        "BACKUP_DATABASE_URL": "unused",
        "BACKUP_KEY_ID": "test",
        "BACKUP_HEARTBEAT_URL": "https://heartbeat.invalid",
    }
    monkeypatch.setattr(backup, "config", lambda: (values, b"x" * 32))
    monkeypatch.setattr(
        backup, "dump_database", lambda url, path: path.write_bytes(b"dump")
    )
    events = []

    class Client:
        def upload_file(self, *args):
            events.append("upload")

        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(b"corrupt")}

        def put_object(self, **kwargs):
            events.append("manifest")

    monkeypatch.setattr(backup.boto3, "client", lambda *args, **kwargs: Client())
    monkeypatch.setattr(
        backup.httpx, "get", lambda *args, **kwargs: events.append("heartbeat")
    )
    with pytest.raises(ValueError):
        backup.run()
    assert events == ["upload"]


def test_database_connection_fields(monkeypatch):
    monkeypatch.setenv("PGSERVICE", "unrelated")
    env = backup.connection_environment(
        "postgresql+asyncpg://user:p%40ss@postgres.railway.internal:5432/railway?sslmode=require"
    )
    assert env["PGHOST"] == "postgres.railway.internal"
    assert env["PGDATABASE"] == "railway"
    assert env["PGPASSWORD"] == "p@ss"
    assert env["PGSSLMODE"] == "require"
    assert "PGSERVICE" not in env
