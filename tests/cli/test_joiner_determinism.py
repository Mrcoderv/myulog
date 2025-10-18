from ulog.cli import MultiLineJoiner


def test_joiner_deduplicates_and_orders_by_stream_key():
    j = MultiLineJoiner()
    a = {"@timestamp":"2025-01-01T00:00:00Z","source":"A","@message":"line1"}
    b = {"@timestamp":"2025-01-01T00:00:00Z","source":"A","@message":"  cont"}
    c = {"@timestamp":"2025-01-01T00:00:00Z","source":"B","@message":"x"}
    # feed mixed order
    assert j.feed(a)[0] is None
    assert j.feed(c)[0] is None
    flushed, _ = j.feed(b)
    # Flushing A should not merge with B despite identical timestamps
    if flushed:
        ts, stream, joined = flushed
        assert stream == "A"
        assert joined == "line1\n  cont"
    # Draining returns the remaining stream B
    drained = j.drain()
    assert any(s == "B" and "x" in msg for _, s, msg in drained)
