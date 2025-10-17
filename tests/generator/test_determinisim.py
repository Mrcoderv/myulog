import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from data.generator.generator import GenerateLog  # replace with actual module name


def test_determinism_integer():
    g1 = GenerateLog([], 1, 123, [])
    g2 = GenerateLog([], 1, 123, [])
    values1 = [g1.generate_integer(0, 100) for _ in range(5)]
    values2 = [g2.generate_integer(0, 100) for _ in range(5)]
    assert values1 == values2, "generate_integer should be deterministic for same seed"


def test_determinism_float():
    g1 = GenerateLog([], 1, 123, [])
    g2 = GenerateLog([], 1, 123, [])
    values1 = [g1.generate_float(0, 1) for _ in range(5)]
    values2 = [g2.generate_float(0, 1) for _ in range(5)]
    assert values1 == values2, "generate_float should be deterministic for same seed"


def test_determinism_string():
    g1 = GenerateLog([], 1, 123, [])
    g2 = GenerateLog([], 1, 123, [])
    strings1 = [g1.generate_string(10) for _ in range(3)]
    strings2 = [g2.generate_string(10) for _ in range(3)]
    assert strings1 == strings2, "generate_string should be deterministic for same seed"


def test_determinism_timestamp():
    g1 = GenerateLog([], 1, 123, [])
    g2 = GenerateLog([], 1, 123, [])
    ts1 = [g1.generate_timestamp() for _ in range(3)]
    ts2 = [g2.generate_timestamp() for _ in range(3)]
    assert ts1 == ts2, "generate_timestamp should be deterministic for same seed"


def test_nondeterminism_unique_string():
    """UUID-based strings must *not* be deterministic."""
    g1 = GenerateLog([], 1, 123, [])
    s1 = g1.generate_unique_string()
    s2 = g1.generate_unique_string()
    assert s1 != s2, "generate_unique_string should not be deterministic"
