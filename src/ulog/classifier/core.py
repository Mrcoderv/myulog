import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .normalizer_adapter import NormalizerAdapter
from .rule_evaluator import RuleEvaluator
from .validator import SchemaValidator

__all__ = ["ClassifierPipeline", "NormalizerAdapter"]


class ClassifierPipeline:
    """
    Orchestrates: parse -> (optional) validate -> classify.
    Validation is non-blocking: if schema is unknown, we skip it but still classify.
    """

    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation
        self.normalizer_adapter = NormalizerAdapter()
        self.validator = SchemaValidator()
        self.rule_evaluator = RuleEvaluator()

    # ---------- Input format handling ----------

    def _guess_format(self, sample_records: List[Dict[str, Any]]) -> str:
        for r in sample_records[:50]:
            if isinstance(r, dict):
                if "@message" in r:  # raw-like
                    return "raw"
                if "timestamp" in r and "meta" in r:  # normalized-like
                    return "json"
        if any(isinstance(r, dict) and "@message" in r for r in sample_records):
            return "raw"
        return "json"

    # ---------- Schema inference (optional) ----------

    def infer_schema(self, record: Dict[str, Any]) -> Optional[str]:
        meta = record.get("meta", {})
        parse = meta.get("parse", {})

        dom = parse.get("domain")
        if dom in {"core_api", "llm", "agentic", "cv"}:
            return dom

        if any(k in record for k in ("event_type", "http_status", "endpoint", "action", "service")):
            return "core_api"
        if any(
            k in record
            for k in ("pipeline_stage", "usage", "ttft_ms", "sampler", "finish_reason", "request_id", "model")
        ):
            return "llm"
        if any(k in record for k in ("step_kind", "workflow_id", "tool_name", "plan_id", "ranked_tools")):
            return "agentic"
        if any(k in record for k in ("phase", "model_name", "dataset_id", "metrics", "hardware", "image_count")):
            return "cv"

        pid = parse.get("pattern_id")
        if isinstance(pid, str):
            s = pid.lower()
            if "agent" in s:
                return "agentic"
            if "http" in s or "apprunner" in s or "build" in s:
                return "core_api"
            if "token" in s or "kv_cache" in s or "llm" in s:
                return "llm"
            if "infer" in s or "cv" in s or "batch" in s:
                return "cv"
        return None

    # ---------- Public entry points ----------

    def process_stream(
        self, input_stream, input_format: str = "auto", schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        input_data: List[Dict[str, Any]] = []
        for line in input_stream:
            line = line.strip()
            if not line:
                continue
            try:
                input_data.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if input_format == "auto":
            input_format = self._guess_format(input_data)

        return self.process_input(input_data, input_format, schema)

    def process_input(
        self, input_data: List[Dict[str, Any]], input_format: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process records with input_format: 'auto' | 'raw' | 'json'.
        Validation runs iff enabled AND (schema provided or inferred).
        Classification always runs; never blocked by validation.
        """
        if input_format == "auto":
            input_format = self._guess_format(input_data)

        # 1) Normalize
        if input_format == "raw":
            normalized = self.normalizer_adapter.process_raw_input(input_data)
        else:  # 'json' path tolerates raw-like dicts with @message
            normalized = self.normalizer_adapter.process_json_input(input_data)

        outputs: List[Dict[str, Any]] = []
        for rec in normalized:
            ok_parse = bool(rec.get("meta", {}).get("parse", {}).get("ok"))
            if not ok_parse:
                outputs.append(rec)
                continue

            # 2) Validation (optional)
            effective_schema = schema or self.infer_schema(rec)
            validation_attempted = False
            validation_ok = None
            validation_errors: Optional[List[str]] = None

            if self.enable_validation and effective_schema:
                validation_attempted = True
                validation_ok, validation_errors = self._validate_record(rec, effective_schema)

            vmeta = rec.setdefault("meta", {}).setdefault("validation", {})
            if validation_attempted:
                vmeta["schema"] = effective_schema
                vmeta["ok"] = bool(validation_ok)
                if not validation_ok and validation_errors:
                    vmeta["errors"] = validation_errors
            else:
                vmeta["skipped"] = True

            # 3) Classification
            classified = self._classify_record(rec, effective_schema)
            outputs.append(classified)

        return outputs

    # ---------- Helpers ----------

    def _validate_record(self, rec: Dict[str, Any], schema: str) -> Tuple[bool, Optional[List[str]]]:
        try:
            self.validator.validate(rec, schema)
            return True, None
        except Exception as e:
            return False, [str(e)]

    def _classify_record(self, rec: Dict[str, Any], schema: Optional[str]) -> Dict[str, Any]:
        evaluator = self.rule_evaluator
        for name in ("apply", "evaluate", "classify", "apply_rules", "evaluate_one"):
            if hasattr(evaluator, name):
                func = getattr(evaluator, name)
                try:
                    try:
                        res = func(rec, domain=schema)
                    except TypeError:
                        res = func(rec)
                    return res if res is not None else rec
                except Exception as e:
                    rec.setdefault("meta", {}).setdefault("classifier", {})["error"] = str(e)
                    return rec

        rec.setdefault("meta", {}).setdefault("classifier", {})["error"] = "rule_evaluator_api_not_found"
        rec.setdefault("provenance", {}).setdefault("parser_rule_id", None)
        return rec

    # ---------- Stats ----------

    def get_processing_stats(self, results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        total = parsed = failed = validated_ok = validated_fail = validated_skipped = classified = 0
        reasons: Dict[str, int] = {}

        for r in results:
            total += 1
            pmeta = r.get("meta", {}).get("parse", {})
            if pmeta.get("ok"):
                parsed += 1
            else:
                failed += 1
                # Prefer explicit unparsed_reason; fallback to parser error; then generic.
                reason = r.get("unparsed_reason") or pmeta.get("error") or "parse_error"
                reasons[reason] = reasons.get(reason, 0) + 1

            vmeta = r.get("meta", {}).get("validation", {})
            if vmeta.get("skipped"):
                validated_skipped += 1
            elif "ok" in vmeta:
                if vmeta["ok"]:
                    validated_ok += 1
                else:
                    validated_fail += 1

            if r.get("provenance", {}).get("parser_rule_id"):
                classified += 1

        parse_rate = (parsed / total * 100.0) if total else 0.0
        return {
            "total": total,
            "parsed": parsed,
            "failed": failed,
            "parse_rate": parse_rate,
            "validated": validated_ok,
            "validation_failed": validated_fail,
            "validation_skipped": validated_skipped,
            "classified": classified,
            "failure_reasons": reasons,
        }
