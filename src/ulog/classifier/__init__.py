"""ULog Classifier Package.

A local-first classifier that runs the full pipeline:
raw|json → parse → validate(schema) → classify(first-match) → annotate
"""

from .core import ClassifierPipeline
from .normalizer_adapter import NormalizerAdapter
from .rule_evaluator import RuleEvaluator
from .validator import SchemaValidator

__version__ = "1.0.0"
__all__ = ["ClassifierPipeline", "NormalizerAdapter", "RuleEvaluator", "SchemaValidator"]
