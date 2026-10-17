import io
import json
import socket
import uuid
from datetime import datetime

import backup
import httpx
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


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
        backup, "dump_database", lambda url, path, **kwargs: path.write_bytes(b"dump")
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


@pytest.fixture
def offline_run(monkeypatch):
    """Real encryption/checksums/snapshot with in-memory storage and no providers."""
    from test_recordings import Store

    source, target = Store(), Store()
    target.data.clear()
    values = {
        "BACKUP_ENDPOINT_URL": "https://storage.invalid/SECRET",
        "BACKUP_ACCESS_KEY_ID": "SECRET",
        "BACKUP_SECRET_ACCESS_KEY": "SECRET",
        "BACKUP_BUCKET": "target",
        "BACKUP_DATABASE_URL": "SECRET",
        "BACKUP_KEY_ID": "test",
        "BACKUP_HEARTBEAT_URL": "https://heartbeat.invalid/SECRET",
        "RECORDING_SOURCE_BUCKET": "source",
        "RECORDING_SOURCE_ACCESS_KEY_ID": "SECRET",
        "RECORDING_SOURCE_SECRET_ACCESS_KEY": "SECRET",
    }
    monkeypatch.setattr(backup, "config", lambda: (values, b"x" * 32))
    clients = iter([target, source])
    monkeypatch.setattr(backup.boto3, "client", lambda *a, **kw: next(clients))
    monkeypatch.setattr(
        backup, "dump_database", lambda url, path, **kwargs: path.write_bytes(b"dump")
    )
    calls = []

    def heartbeat(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(backup.httpx, "get", heartbeat)
    return source, target, calls


def events(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_complete_audit_and_legacy_manifest_compatibility(offline_run, capsys):
    _, target, calls = offline_run
    backup.run()
    records = events(capsys)
    execution_id = records[0]["execution_id"]
    assert uuid.UUID(execution_id).version == 4
    assert {item["execution_id"] for item in records} == {execution_id}
    assert [item["sequence"] for item in records] == list(range(1, len(records) + 1))
    elapsed = [item["elapsed_seconds"] for item in records]
    assert elapsed == sorted(elapsed) and min(elapsed) >= 0
    for item in records:
        assert datetime.fromisoformat(item["event_at"]).utcoffset().total_seconds() == 0
        assert item["audit_schema_version"] == 1
        assert item["outcome"] in {"success", "started", "observed"}
    names = [item["event"] for item in records]
    expected = [
        "database_verified",
        "database_manifest_published",
        "recording_object_verified",
        "recording_inventory_checked",
        "recordings_verified",
        "recording_manifest_published",
        "verification_completed",
        "heartbeat_request_started",
        "heartbeat_response_received",
        "heartbeat_request_completed",
        "application_completed",
    ]
    assert [names.index(name) for name in expected] == sorted(
        names.index(name) for name in expected
    )
    assert calls == [{"timeout": 15, "follow_redirects": False}]
    assert records[-1]["intended_exit_code"] == 0
    assert records[-1]["platform_termination_confirmed"] is False
    database, recording = target.manifests
    for manifest in target.manifests:
        assert manifest["execution_id"] == execution_id
        assert manifest["audit_schema_version"] == 1
    assert set(database) - {"execution_id", "audit_schema_version"} == {
        "format",
        "created_at",
        "object_key",
        "sha256",
        "plaintext_bytes",
        "encrypted_bytes",
        "key_id",
        "verified_download",
        "scope",
    }
    assert set(recording) - {"execution_id", "audit_schema_version"} == {
        "format",
        "source_bucket",
        "objects",
        "verified_download",
        "database_atomic_snapshot",
    }
    assert database["format"] == "COSBACKUP1"
    assert recording["format"] == "COSRECORDINGS1"
    assert database["verified_download"] and recording["verified_download"]
    assert recording["database_atomic_snapshot"] is False
    assert database["object_key"].endswith(execution_id + ".dump.aesgcm")
    assert decrypt(target.data[database["object_key"]], b"x" * 32) == b"dump"
    obj = recording["objects"][0]
    assert decrypt(target.data[obj["backup_key"]], b"x" * 32) == b"synthetic audio"
    # Legacy consumers need no audit fields to locate/authenticate the same payload.
    legacy = {
        k: v
        for k, v in database.items()
        if k not in {"execution_id", "audit_schema_version"}
    }
    assert decrypt(target.data[legacy["object_key"]], b"x" * 32) == b"dump"
    assert "SECRET" not in json.dumps(records)
    assert "synthetic.wav" not in json.dumps(records)


@pytest.mark.parametrize(
    "stage",
    [
        "configuration",
        "client",
        "database_export",
        "encryption",
        "hash",
        "database_upload",
        "database_verification",
        "database_manifest",
        "recording_inventory",
        "recording_read",
        "recording_upload",
        "recording_verification",
        "recording_manifest",
        "cleanup",
    ],
)
def test_stage_failure_preserves_exception_and_blocks_heartbeat(
    stage, offline_run, monkeypatch, capsys
):
    source, target, calls = offline_run
    failure = RuntimeError("SECRET https://private.invalid/token tenant-content")

    def fail(*args, **kwargs):
        raise failure

    direct = {
        "configuration": "config",
        "database_export": "dump_database",
        "encryption": "encrypt_file",
        "hash": "file_hash",
    }
    if stage in direct:
        monkeypatch.setattr(backup, direct[stage], fail)
    elif stage == "client":
        monkeypatch.setattr(backup.boto3, "client", fail)
    elif stage == "recording_inventory":
        monkeypatch.setattr(source, "paginate", fail)
    elif stage == "recording_read":
        monkeypatch.setattr(source, "get_object", fail)
    elif stage == "cleanup":
        original = backup.tempfile.TemporaryDirectory

        class CleanupFailure:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def __enter__(self):
                self.inner = original(**self.kwargs)
                return self.inner.__enter__()

            def __exit__(self, *args):
                self.inner.__exit__(*args)
                raise failure

        monkeypatch.setattr(backup.tempfile, "TemporaryDirectory", CleanupFailure)
    else:
        operation = (
            "put_object"
            if stage.endswith("manifest")
            else ("upload_file" if stage.endswith("upload") else "get_object")
        )
        original = getattr(target, operation)

        def selected(*args, **kwargs):
            key = args[2] if operation == "upload_file" else kwargs["Key"]
            if key.startswith(
                "postgres/" if stage.startswith("database") else "recordings/"
            ):
                raise failure
            return original(*args, **kwargs)

        monkeypatch.setattr(target, operation, selected)
    with pytest.raises(RuntimeError) as caught:
        backup.run()
    assert caught.value is failure
    records = events(capsys)
    assert calls == []
    assert records[-1]["event"] == "application_failed"
    assert records[-1]["intended_exit_code"] == 1
    assert not any(
        item["event"] in {"verification_completed", "application_completed"}
        for item in records
    )
    assert len({item["execution_id"] for item in records}) == 1
    assert "SECRET" not in json.dumps(records)
    assert "tenant-content" not in json.dumps(records)
    if stage.startswith("recording") or stage == "cleanup":
        assert target.manifests[0]["format"] == "COSBACKUP1"


@pytest.mark.parametrize("status", [301, 400, 401, 429, 500])
def test_heartbeat_http_failure(status, offline_run, monkeypatch, capsys):
    def heartbeat(url, **kwargs):
        return httpx.Response(status, text="SECRET", request=httpx.Request("GET", url))

    monkeypatch.setattr(backup.httpx, "get", heartbeat)
    with pytest.raises(httpx.HTTPStatusError):
        backup.run()
    records = events(capsys)
    response = next(
        item for item in records if item["event"] == "heartbeat_response_received"
    )
    assert response["http_status"] == status
    assert response["request_duration_seconds"] >= 0
    assert (
        next(item for item in records if item["event"] == "heartbeat_failed")[
            "error_category"
        ]
        == "http_status"
    )
    assert records[-1]["event"] == "application_failed"
    assert "SECRET" not in json.dumps(records)


@pytest.mark.parametrize(
    "error_type", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError]
)
def test_heartbeat_transport_receipt_unknown(
    error_type, offline_run, monkeypatch, capsys
):
    receiver = []
    failure = error_type("SECRET")

    def heartbeat(*args, **kwargs):
        if error_type is httpx.ReadTimeout:
            receiver.append("accepted")  # Acceptance can precede a lost response.
        raise failure

    monkeypatch.setattr(backup.httpx, "get", heartbeat)
    with pytest.raises(error_type) as caught:
        backup.run()
    assert caught.value is failure
    records = events(capsys)
    result = next(item for item in records if item["event"] == "heartbeat_failed")
    assert result["receipt"] == "unknown"
    assert result["error_category"] == (
        "transport" if error_type is httpx.ConnectError else "timeout"
    )
    assert "http_status" not in result
    assert "SECRET" not in json.dumps(records)
    assert records[-1]["event"] == "application_failed"
    if error_type is httpx.ReadTimeout:
        assert receiver == ["accepted"]


@pytest.mark.parametrize("failure", [False, True])
def test_broken_audit_sink_does_not_change_outcome(failure, offline_run, monkeypatch):
    original_error = ValueError("original")

    def broken_print(*args, **kwargs):
        raise BrokenPipeError("log sink unavailable")

    def fail():
        raise original_error

    monkeypatch.setattr("builtins.print", broken_print)
    if failure:
        monkeypatch.setattr(backup, "config", fail)
        with pytest.raises(ValueError) as caught:
            backup.run()
        assert caught.value is original_error
    else:
        backup.run()
        assert len(offline_run[2]) == 1


def test_empty_inventory_is_reported_without_changing_behavior(offline_run, capsys):
    source, target, calls = offline_run
    source.data.clear()
    backup.run()
    records = events(capsys)
    checked = next(
        item for item in records if item["event"] == "recording_inventory_checked"
    )
    assert checked["expected_count"] == checked["verified_count"] == 0
    assert target.manifests[1]["objects"] == []
    assert len(calls) == 1


def test_inventory_change_blocks_entire_run(offline_run, monkeypatch, capsys):
    source, target, calls = offline_run
    original = source.paginate
    inventories = []

    def changed(**kwargs):
        inventories.append(1)
        return original(**kwargs) if len(inventories) == 1 else [{"Contents": []}]

    monkeypatch.setattr(source, "paginate", changed)
    with pytest.raises(ValueError, match="inventory changed"):
        backup.run()
    records = events(capsys)
    assert calls == []
    assert len(target.manifests) == 1
    assert records[-1]["event"] == "application_failed"
    assert not any(item["event"] == "verification_completed" for item in records)


def test_export_diagnostic_is_correlated_and_safe_with_broken_sink(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    monkeypatch.setattr(backup, "connection_environment", lambda url: {})
    monkeypatch.setattr(
        backup.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=7, stderr=b"permission denied SECRET"
        ),
    )
    records = []
    monkeypatch.setattr(
        "builtins.print", lambda text, **kwargs: records.append(json.loads(text))
    )
    audit = backup.Audit()
    with pytest.raises(RuntimeError, match="Database export failed"):
        backup.dump_database("unused", tmp_path / "missing", audit=audit)
    assert records[0]["execution_id"] == audit.execution_id
    assert records[0]["subprocess_exit_code"] == 7
    assert "SECRET" not in json.dumps(records)

    def broken(*args, **kwargs):
        raise BrokenPipeError("sink")

    monkeypatch.setattr("builtins.print", broken)
    with pytest.raises(RuntimeError, match="Database export failed"):
        backup.dump_database("unused", tmp_path / "missing", audit=audit)
