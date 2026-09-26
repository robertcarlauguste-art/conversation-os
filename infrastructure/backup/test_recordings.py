import io
import json

import backup
import pytest
import recordings


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


def perform(source, target, tmp_path, limit=1024):
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
