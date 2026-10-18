import io
import json
import socket

import backup
import pytest
import recordings


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access forbidden in offline tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


class Store:
    def __init__(self):
        self.data = {"conversations/synthetic.wav": b"synthetic audio"}
        self.manifests = []

    def get_paginator(self, name):
        return self

    def paginate(self, **kwargs):
        return [
            {
                "Contents": [
                    {"Key": key, "Size": len(value), "ETag": "etag"}
                    for key, value in self.data.items()
                ]
            }
        ]

    def get_object(self, **kwargs):
        if kwargs["Bucket"] == "source":
            assert kwargs["IfMatch"] == "etag"
        return {"Body": io.BytesIO(self.data[kwargs["Key"]])}

    def upload_file(self, path, bucket, key):
        self.data[key] = backup.Path(path).read_bytes()

    def put_object(self, **kwargs):
        self.manifests.append(json.loads(kwargs["Body"]))


def perform(source, target, tmp_path, limit=1024, audit=None):
    return recordings.snapshot(
        source,
        "source",
        target,
        "target",
        "snapshot",
        b"x" * 32,
        tmp_path,
        backup.encrypt_file,
        backup.verify_remote,
        backup.file_hash,
        limit,
        audit=audit,
    )


def test_snapshot_verifies_copy_without_changing_source(tmp_path):
    source, target = Store(), Store()
    original = dict(source.data)
    assert perform(source, target, tmp_path) == 1
    assert source.data == original
    assert target.manifests[0]["verified_download"]
    assert target.manifests[0]["objects"][0]["plaintext_bytes"] == 15


def test_size_limit_prevents_manifest(tmp_path):
    source, target = Store(), Store()
    with pytest.raises(ValueError):
        perform(source, target, tmp_path, limit=1)
    assert target.manifests == []


def test_source_change_prevents_manifest(tmp_path):
    source, target = Store(), Store()
    original = source.paginate
    calls = []

    def changing(**kwargs):
        calls.append(1)
        if len(calls) > 1:
            return [{"Contents": []}]
        return original(**kwargs)

    source.paginate = changing
    with pytest.raises(ValueError, match="changed"):
        perform(source, target, tmp_path)
    assert target.manifests == []


def test_optional_audit_preserves_legacy_manifest(tmp_path):
    source, target = Store(), Store()
    perform(source, target, tmp_path)
    assert set(target.manifests[0]) == {
        "format",
        "source_bucket",
        "objects",
        "verified_download",
        "database_atomic_snapshot",
    }
    assert target.manifests[0]["format"] == "COSRECORDINGS1"


@pytest.mark.parametrize("mismatch", ["inventory", "ciphertext"])
def test_verification_failure_has_no_manifest_or_completion(
    tmp_path, monkeypatch, capsys, mismatch
):
    source, target = Store(), Store()
    if mismatch == "inventory":
        original = source.paginate
        calls = []

        def changed(**kwargs):
            calls.append(1)
            return original(**kwargs) if len(calls) == 1 else [{"Contents": []}]

        monkeypatch.setattr(source, "paginate", changed)
    else:
        monkeypatch.setattr(
            target, "get_object", lambda **kwargs: {"Body": io.BytesIO(b"corrupt")}
        )
    with pytest.raises(ValueError):
        perform(source, target, tmp_path, audit=backup.Audit())
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert target.manifests == []
    assert not any(
        item["event"] in {"recordings_verified", "recording_manifest_published"}
        for item in records
    )
    if mismatch == "inventory":
        assert records[-1]["outcome"] == "failure"
