import ulog


def test_echo_roundtrip():
    assert ulog.echo("ULog") == "ULog"


def test_version_exists():
    assert isinstance(ulog.__version__, str) and len(ulog.__version__) > 0
