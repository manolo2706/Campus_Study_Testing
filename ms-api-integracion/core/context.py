import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")

REQUEST_ID_HEADER = "X-Request-ID"


def set_request_id(value: str | None = None) -> str:
    rid = value or str(uuid.uuid4())
    _request_id.set(rid)
    return rid


def get_request_id() -> str:
    rid = _request_id.get()
    if not rid:
        rid = set_request_id()
    return rid
