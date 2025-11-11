
class MultiLineJoiner:
    """
    Deterministic multi-line joiner.

    Test contract:
    - feed(event: dict) -> (optional_flushed, aux)
      * optional_flushed: None or (timestamp:str, stream_key:str, joined_message:str)
      * aux: not used by the tests (can be None)
    - drain() -> list[(timestamp, stream_key, joined_message)]
      * flushes all buffers in deterministic order
    """

    def __init__(self, stream_field: str = "source", ts_field: str = "@timestamp", msg_field: str = "@message"):
        self.stream_field = stream_field
        self.ts_field = ts_field
        self.msg_field = msg_field
        # stream_key -> (timestamp, [lines])
        self._buf: dict[str, tuple[str, list[str]]] = {}

    def _is_continuation(self, s: str) -> bool:
        return isinstance(s, str) and (s.startswith(" ") or s.startswith("\t"))

    def _flush(self, stream: str) -> tuple[str, str, str]:
        ts, lines = self._buf.pop(stream)
        return (ts, stream, "\n".join(lines))

    def feed(self, event: dict):
        # tolerate missing fields; do not break the pipeline
        ts = event.get(self.ts_field)
        msg = event.get(self.msg_field, "")

        # accept several common stream fields, otherwise fallback to a global bucket
        stream = (
            event.get(self.stream_field)
            or event.get("stream")
            or event.get("logger")
            or event.get("component")
            or "__default__"
        )

        if ts is None:
            # without a timestamp we cannot order/join deterministically
            return (None, None)

        if self._is_continuation(msg):
            if stream in self._buf:
                prev_ts, lines = self._buf[stream]
                lines.append(msg)
                self._buf[stream] = (prev_ts, lines)
                flushed = self._flush(stream)
                return (flushed, None)
            else:
                # no prior buffer: treat as standalone
                return ((ts, stream, msg), None)
        else:
            flushed = None
            if stream in self._buf:
                flushed = self._flush(stream)
            self._buf[stream] = (ts, [msg])
            return (flushed, None)

    def drain(self) -> list[tuple[str, str, str]]:
        # deterministic order: by stream key; adjust if you need a different rule
        streams = sorted(self._buf.keys())
        out = [self._flush(s) for s in streams]
        return out