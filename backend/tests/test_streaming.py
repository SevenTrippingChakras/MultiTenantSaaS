"""Phase 8 streaming control: heartbeat injection + stop-event cancellation.

Pure unit tests — no DB or Redis. They drive `with_heartbeat` over fake async
sources so the racing/cancellation logic is exercised offline.
"""

import asyncio

from app.core.streaming import HEARTBEAT, with_heartbeat


async def _drain(agen) -> list[str]:
    return [item async for item in agen]


async def test_passes_items_through_without_heartbeat():
    async def source():
        for tok in ["a", "b", "c"]:
            yield tok

    out = await _drain(with_heartbeat(source(), interval=10.0))
    assert out == ["a", "b", "c"]


async def test_injects_heartbeat_while_source_is_idle():
    async def source():
        yield "a"
        await asyncio.sleep(0.05)  # long pause relative to the interval
        yield "b"

    out = await _drain(with_heartbeat(source(), interval=0.01))
    assert out[0] == "a"
    assert HEARTBEAT in out  # at least one ping during the pause
    assert out[-1] == "b"
    assert [x for x in out if x != HEARTBEAT] == ["a", "b"]


async def test_stop_event_ends_relay_and_finalizes_source():
    finalized = asyncio.Event()
    stop = asyncio.Event()

    async def source():
        try:
            yield "a"
            stop.set()  # ask to stop after the first token
            await asyncio.sleep(10)  # would hang forever if not cancelled
            yield "b"
        finally:
            finalized.set()  # source's cleanup must still run

    out = await _drain(with_heartbeat(source(), interval=10.0, stop=stop))
    assert out == ["a"]  # stopped before "b"
    assert finalized.is_set()  # cancellation propagated into the source
