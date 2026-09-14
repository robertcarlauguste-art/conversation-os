"""Durable transition alerts with bounded, content-free payloads."""

import json
import os
from pathlib import Path

import httpx

from app.core.config import Settings


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "incidents": {}}
    state = json.loads(path.read_text())
    if state.get("version") != 1 or not isinstance(state.get("incidents"), dict):
        raise ValueError("Invalid monitor state")
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


async def process_signals(
    signals: dict[str, bool | None], state: dict, settings: Settings, client: httpx.AsyncClient
) -> list[dict]:
    events = []
    for code, unhealthy in sorted(signals.items()):
        incident = state["incidents"].setdefault(code, {"bad": 0, "good": 0, "sent": False})
        if unhealthy is None:
            incident.update(bad=0, good=0)
            continue
        incident["bad"] = (
            min(incident["bad"] + 1, settings.monitoring_consecutive_checks) if unhealthy else 0
        )
        incident["good"] = (
            min(incident["good"] + 1, settings.monitoring_consecutive_checks)
            if not unhealthy
            else 0
        )
        firing = (
            unhealthy
            and incident["bad"] >= settings.monitoring_consecutive_checks
            and not incident["sent"]
        )
        recovery = (
            not unhealthy
            and incident["good"] >= settings.monitoring_consecutive_checks
            and incident["sent"]
        )
        if not (firing or recovery):
            continue
        event = {
            "service": "ConversationOS",
            "environment": settings.app_env,
            "code": code,
            "status": "firing" if firing else "resolved",
        }
        if settings.monitoring_webhook_url is None:
            events.append(event | {"delivery": "disabled"})
            continue
        try:
            response = await client.post(settings.monitoring_webhook_url, json=event)
            if not 200 <= response.status_code < 300:
                raise ValueError("Delivery rejected")
        except Exception:
            events.append(event | {"delivery": "failed"})
            continue
        incident["sent"] = bool(firing)
        events.append(event | {"delivery": "accepted"})
    return events


async def heartbeat(settings: Settings, events: list[dict], client: httpx.AsyncClient) -> str:
    """Ping an independent missing-heartbeat service after durable poll completion."""
    if settings.monitoring_heartbeat_url is None:
        return "disabled"
    if any(event["delivery"] != "accepted" for event in events):
        return "withheld"
    try:
        response = await client.get(settings.monitoring_heartbeat_url)
        return "accepted" if 200 <= response.status_code < 300 else "failed"
    except Exception:
        return "failed"
