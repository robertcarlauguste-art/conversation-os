"""Run as a separate single-replica service with a persistent /data volume."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.monitoring.probes import collect
from app.monitoring.service import heartbeat, load_state, process_signals, save_state


async def run(once: bool = False) -> None:
    settings = get_settings()
    if settings.monitoring_api_url is None:
        raise ValueError("MONITORING_API_URL is required")
    path = Path(settings.monitoring_state_path)
    state = load_state(path)
    # Prove state persistence is writable before sending any notifications.
    save_state(path, state)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            while True:
                signals = await collect(settings, engine)
                events = await process_signals(signals, state, settings, client)
                save_state(path, state)
                heartbeat_status = await heartbeat(settings, events, client)
                print(
                    json.dumps(
                        {
                            "event": "monitor_poll",
                            "signals": signals,
                            "notifications": events,
                            "heartbeat": heartbeat_status,
                        }
                    ),
                    flush=True,
                )
                if once:
                    return
                await asyncio.sleep(settings.monitoring_interval_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(run("--once" in sys.argv))
    except KeyboardInterrupt:
        pass
    except Exception:
        # Exception text may contain database credentials or webhook URLs.
        print("monitor_unavailable: check configuration, state volume and dependencies", flush=True)
        raise SystemExit(1) from None
