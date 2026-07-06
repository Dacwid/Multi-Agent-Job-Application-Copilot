"""Per-application event queues so the SSE endpoint can stream node-level
progress while the graph runs in a background thread. queue.Queue is
thread-safe, so parallel graph nodes (which LangGraph runs on separate
threads) can all push into the same queue safely."""

import queue

_queues: dict[str, "queue.Queue[dict]"] = {}


def register_queue(application_id: str) -> "queue.Queue[dict]":
    q: "queue.Queue[dict]" = queue.Queue()
    _queues[application_id] = q
    return q


def unregister_queue(application_id: str) -> None:
    _queues.pop(application_id, None)


def emit(application_id: str, event: dict) -> None:
    q = _queues.get(application_id)
    if q is not None:
        q.put(event)
