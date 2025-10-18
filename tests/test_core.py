"""Tests for core module."""

from ulog.core import echo


def test_echo():
    """Test echo function."""
    assert echo("hello") == "hello"
    assert echo("") == ""
    assert echo("test message") == "test message"
