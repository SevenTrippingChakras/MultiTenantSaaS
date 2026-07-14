import asyncio
import contextlib
from collections.abc import AsyncIterator

# An SSE comment line (starts with ':'). Clients ignore it, but it is real
# traffic, so proxies and load balancers don't cut an idle stream.
HEARTBEAT = ": ping\n\n"


async def with_heartbeat(
    source: AsyncIterator[str],
    interval: float,
    stop: asyncio.Event | None = None,
) -> AsyncIterator[str]:
    """Relay `source`, injecting `: ping` comments while it is idle.

    Each next item is fetched as a task and raced against `interval` (and the
    `stop` event, if given). On timeout a heartbeat is emitted and the *same*
    fetch keeps running, so a slow model shows as pings, not silence. When
    `stop` is set the relay ends and the pending fetch is cancelled; that
    cancellation propagates into `source`, whose own `finally` closes the
    upstream call and persists any partial reply.
    """
    it = source.__aiter__()
    item_task: asyncio.Task[str] | None = None
    stop_task = asyncio.ensure_future(stop.wait()) if stop is not None else None
    try:
        while True:
            if item_task is None:
                item_task = asyncio.ensure_future(anext(it))
            waiters: set[asyncio.Task] = {item_task}
            if stop_task is not None:
                waiters.add(stop_task)
            done, _ = await asyncio.wait(
                waiters, timeout=interval, return_when=asyncio.FIRST_COMPLETED
            )
            if stop_task is not None and stop_task in done:
                return
            if item_task not in done:
                yield HEARTBEAT
                continue
            try:
                item = item_task.result()
            except StopAsyncIteration:
                return
            finally:
                item_task = None
            yield item
    finally:
        # Cancelling the in-flight fetch runs `source`'s finally (persist +
        # upstream close). Await it so that cleanup completes before we exit.
        if item_task is not None and not item_task.done():
            item_task.cancel()
            with contextlib.suppress(BaseException):
                await item_task
        if stop_task is not None and not stop_task.done():
            stop_task.cancel()
