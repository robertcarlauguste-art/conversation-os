import json
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.monitoring.probes import collect
from app.monitoring.service import heartbeat, load_state, process_signals, save_state


def settings(**kwargs):
    if kwargs.get("storage_backend") == "s3":
        kwargs.update(
            s3_endpoint_url="https://storage.test",
            s3_region="auto",
            s3_bucket="test",
            s3_access_key_id="test",
            s3_secret_access_key="test",
        )
    return Settings(
        _env_file=None, monitoring_webhook_url="https://alerts.example.test/secret", **kwargs
    )


async def test_free_heartbeat_refresh_failure_restart_and_confirmed_recovery(tmp_path):
    requests = []

    def receive(request):
        requests.append(request)
        return httpx.Response(204)

    config = Settings(_env_file=None, monitoring_alert_heartbeat_url="https://heartbeat.test/key")
    path = tmp_path / "state.json"
    state = load_state(path)
    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
        for value in (False, False, False, True, True, None, False, False):
            await process_signals({"database_unavailable": value}, state, config, client)
            save_state(path, state)
            state = load_state(path)
    assert [request.url.path for request in requests] == [
        "/key",
        "/key",
        "/key/fail",
        "/key/fail",
        "/key/fail",
        "/key",
    ]
    assert all(request.method == "GET" and not request.content for request in requests)
    assert "key" not in path.read_text()


async def test_free_heartbeat_unknown_never_reports_healthy_and_failure_retries():
    config = Settings(
        _env_file=None,
        monitoring_alert_heartbeat_url="https://heartbeat.test/key",
        monitoring_consecutive_checks=1,
    )
    client = Mock(get=AsyncMock(side_effect=[httpx.Response(503), httpx.Response(204)]))
    state = {"incidents": {}}
    for signals in ({}, {"a": None}, {"a": False, "b": None}):
        assert await process_signals(signals, state, config, client) == []
    client.get.assert_not_called()
    events = await process_signals({"a": True, "b": None}, state, config, client)
    assert events[0]["delivery"] == "failed"
    assert not state["incidents"]["operational_health"]["sent"]
    events = await process_signals({"a": True, "b": None}, state, config, client)
    assert events[0]["delivery"] == "accepted"
    assert state["incidents"]["operational_health"]["sent"]


@pytest.mark.parametrize(
    "extra",
    [
        {"monitoring_webhook_url": "https://alerts.test/key"},
        {"monitoring_heartbeat_url": "https://heartbeat.test/key/"},
        {"monitoring_alert_heartbeat_url": "https://heartbeat.test/key?secret=value"},
        {"monitoring_alert_heartbeat_url": "http://heartbeat.test/key"},
    ],
)
def test_free_heartbeat_rejects_ambiguous_or_unsafe_configuration(extra):
    values = {"monitoring_alert_heartbeat_url": "https://heartbeat.test/key"} | extra
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


async def test_transitions_survive_restart_and_unknown_does_not_resolve(tmp_path):
    sent = []

    def receive(request):
        sent.append(json.loads(request.content))
        return httpx.Response(204)

    path = tmp_path / "state.json"
    state = load_state(path)
    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
        for signal in (True, True, True, None, False):
            await process_signals({"worker_unavailable": signal}, state, settings(), client)
            save_state(path, state)
            state = load_state(path)
        assert [e["status"] for e in sent] == ["firing"]
        await process_signals({"worker_unavailable": False}, state, settings(), client)
    assert [e["status"] for e in sent] == ["firing", "resolved"]
    assert all(set(e) == {"service", "environment", "code", "status"} for e in sent)
    assert "secret" not in path.read_text()


@pytest.mark.parametrize("failure", [httpx.Response(503), httpx.Response(302)])
async def test_delivery_failure_retries_on_next_poll_without_false_ack(failure):
    client = Mock(post=AsyncMock(side_effect=[failure, httpx.Response(202)]))
    state = {"incidents": {}}
    config = settings(monitoring_consecutive_checks=1)
    result = await process_signals({"database_unavailable": True}, state, config, client)
    assert result[0]["delivery"] == "failed"
    assert not state["incidents"]["database_unavailable"]["sent"]
    result = await process_signals({"database_unavailable": True}, state, config, client)
    assert result[0]["delivery"] == "accepted"


async def test_no_credentials_or_exception_body_in_delivery_failure():
    client = Mock(post=AsyncMock(side_effect=RuntimeError("secret token tenant recording")))
    result = await process_signals(
        {"api_unavailable": True},
        {"incidents": {}},
        settings(monitoring_consecutive_checks=1),
        client,
    )
    assert not any(word in json.dumps(result) for word in ("secret", "token", "tenant"))


async def test_disabled_delivery_and_flapping():
    config = Settings(_env_file=None)
    state = {"incidents": {}}
    client = Mock(post=AsyncMock())
    for signal in (True, False, True, False):
        assert await process_signals({"api_unavailable": signal}, state, config, client) == []
    await process_signals({"api_unavailable": True}, state, config, client)
    events = await process_signals({"api_unavailable": True}, state, config, client)
    assert events[0]["delivery"] == "disabled"
    client.post.assert_not_called()
    assert not state["incidents"]["api_unavailable"]["sent"]


def test_corrupt_state_fails_closed(tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"version": 99}')
    with pytest.raises(ValueError):
        load_state(path)


@pytest.mark.parametrize("delivery", ["failed", "disabled"])
async def test_heartbeat_withheld_when_notification_was_not_accepted(delivery):
    client = Mock(get=AsyncMock())
    config = settings(monitoring_heartbeat_url="https://heartbeat.test/private")
    assert await heartbeat(config, [{"delivery": delivery}], client) == "withheld"
    client.get.assert_not_called()


async def test_heartbeat_acceptance_failure_and_disabled():
    client = Mock(get=AsyncMock(side_effect=[httpx.Response(200), RuntimeError("private URL")]))
    config = settings(monitoring_heartbeat_url="https://heartbeat.test/private")
    assert await heartbeat(config, [], client) == "accepted"
    assert await heartbeat(config, [], client) == "failed"
    assert await heartbeat(settings(), [], client) == "disabled"


@pytest.mark.parametrize(
    "url",
    [
        "http://alerts.test",
        "https://user:pass@alerts.test",
        "https://alerts.test/#secret",
        "https://alerts.test:invalid",
    ],
)
def test_webhook_configuration_rejects_unsafe_urls(url):
    with pytest.raises(ValidationError):
        settings(monitoring_api_url=url)


async def test_probe_failures_are_unknown_downstream_and_do_not_expose_errors(monkeypatch):
    monkeypatch.setattr(
        "app.monitoring.probes.processing_counts",
        AsyncMock(side_effect=RuntimeError("private db password")),
    )
    redis = Mock(ping=AsyncMock(side_effect=RuntimeError("private Redis URL")), aclose=AsyncMock())
    monkeypatch.setattr("app.monitoring.probes.Redis.from_url", Mock(return_value=redis))
    monkeypatch.setattr(
        "app.monitoring.probes.boto3.client", Mock(side_effect=RuntimeError("private R2 key"))
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    monkeypatch.setattr("app.monitoring.probes.httpx.AsyncClient", lambda **_: client)
    result = await collect(
        settings(
            processing_mode="queue", storage_backend="s3", monitoring_api_url="https://api.test"
        ),
        Mock(),
    )
    assert result == {
        "api_unavailable": True,
        "database_unavailable": True,
        "processing_failed": None,
        "processing_stalled": None,
        "repeated_provider_failures": None,
        "redis_unavailable": True,
        "worker_unavailable": None,
        "queue_backlog": None,
        "storage_unavailable": True,
    }
    assert "private" not in json.dumps(result)


async def test_probe_thresholds_and_healthy_dependencies(monkeypatch):
    monkeypatch.setattr(
        "app.monitoring.probes.processing_counts",
        AsyncMock(return_value={"failed": 1, "stalled": 1, "provider_failures": 3}),
    )
    redis = Mock(
        ping=AsyncMock(),
        exists=AsyncMock(return_value=1),
        zcard=AsyncMock(return_value=25),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr("app.monitoring.probes.Redis.from_url", Mock(return_value=redis))
    monkeypatch.setattr("app.monitoring.probes.boto3.client", Mock(return_value=Mock()))
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "ok"}))
    )
    monkeypatch.setattr("app.monitoring.probes.httpx.AsyncClient", lambda **_: client)
    result = await collect(
        settings(
            processing_mode="queue", storage_backend="s3", monitoring_api_url="https://api.test"
        ),
        Mock(),
    )
    assert result == {
        "api_unavailable": False,
        "database_unavailable": False,
        "processing_failed": True,
        "processing_stalled": True,
        "repeated_provider_failures": True,
        "redis_unavailable": False,
        "worker_unavailable": False,
        "queue_backlog": True,
        "storage_unavailable": False,
    }
