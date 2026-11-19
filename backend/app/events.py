"""In-memory pub/sub so the dashboard can follow a test run live (Server-Sent Events)."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator


class RunBroker:
    def __init__(self) -> None:
        self.history: dict[int, list[dict]] = defaultdict(list)
        self.subscribers: dict[int, list[asyncio.Queue]] = defaultdict(list)
        self.finished: set[int] = set()

    async def publish(self, run_id: int, event: dict) -> None:
        if event.get("type") != "frame":
            self.history[run_id].append(event)
        else:
            self.history[run_id] = [e for e in self.history[run_id] if e.get("type") != "frame"] + [event]
        if event.get("type") == "run_finished":
            self.finished.add(run_id)
        for queue in self.subscribers[run_id]:
            queue.put_nowait(event)

    async def subscribe(self, run_id: int) -> AsyncIterator[dict]:
        for event in list(self.history[run_id]):
            yield event
        if run_id in self.finished:
            return
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers[run_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("type") == "run_finished":
                    return
        finally:
            self.subscribers[run_id].remove(queue)


broker = RunBroker()
