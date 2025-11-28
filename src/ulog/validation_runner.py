"""
E2E Validation Runner for MyULog
Executes the complete pipeline: parse → validate → classify → annotate
Tests across all 4 domains: Core/API, LLM, Agentic, CV
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


@dataclass
class DomainMetrics:
    """Metrics for a single domain"""
    domain: str
    total_logs: int
    parse_ok: int
    parse_failed: int
    schema_violation: int
    classification_ok: int
    classification_failed: int
    annotation_ok: int
    annotation_failed: int
    parse_rate: float = 0.0
    schema_valid_rate: float = 0.0
    classification_rate: float = 0.0
    annotation_rate: float = 0.0

    def calculate_rates(self) -> None:
        """Calculate success rates"""
        if self.total_logs > 0:
            self.parse_rate = (self.parse_ok / self.total_logs) * 100
            self.schema_valid_rate = ((self.total_logs - self.schema_violation) / self.total_logs) * 100
            self.classification_rate = (self.classification_ok / self.total_logs) * 100
            self.annotation_rate = (self.annotation_ok / self.total_logs) * 100


@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: str
    domains: Dict[str, DomainMetrics]
    total_logs: int
    total_parse_ok: int
    total_failed: int
    overall_success_rate: float = 0.0

    def calculate_overall_rate(self) -> None:
        """Calculate overall success rate"""
        if self.total_logs > 0:
            self.overall_success_rate = (self.total_parse_ok / self.total_logs) * 100


class ValidationRunner:
    """E2E Validation Runner"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize validation runner
        
        Args:
            config_path: Optional path to config file
        """
        self.repo_root = self._find_repo_root()
        self.schemas_dir = Path(os.getenv("ULOG_SCHEMAS_DIR", self.repo_root / "schemas"))
        self.rules_path = Path(os.getenv("ULOG_RULES_PATH", self.repo_root / "rules" / "rules.json"))
        self.vocab_path = Path(os.getenv("ULOG_VOCAB_PATH", self.repo_root / "vocab" / "controlled_vocabulary.json"))
        self.data_dir = Path(os.getenv("ULOG_DATA_DIR", self.repo_root / "data"))
        
        # Ensure directories exist
        self._validate_paths()
        
        logger.info("ValidationRunner initialized")
        logger.info(f"  Schemas: {self.schemas_dir}")
        logger.info(f"  Rules: {self.rules_path}")
        logger.info(f"  Vocab: {self.vocab_path}")

    @staticmethod
    def _find_repo_root() -> Path:
        """Find repository root directory"""
        current = Path(__file__).parent
        while current != current.parent:
            if (current / ".git").exists() or (current / "pyproject.toml").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _validate_paths(self) -> None:
        """Validate required paths exist"""
        if not self.schemas_dir.exists():
            raise FileNotFoundError(f"Schemas directory not found: {self.schemas_dir}")
        if not self.rules_path.exists():
            logger.warning(f"Rules file not found: {self.rules_path}")
        if not self.vocab_path.exists():
            logger.warning(f"Vocabulary file not found: {self.vocab_path}")

    def load_schema(self, domain: str) -> Dict[str, Any]:
        """Load schema for domain"""
        schema_file = self.schemas_dir / f"{domain}_schema.json"
        if not schema_file.exists():
            # Try alternative naming
            schema_file = self.schemas_dir / f"{domain}.schema.json"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema not found for domain: {domain}")
        
        with open(schema_file) as f:
            return json.load(f)

    def load_rules(self) -> Dict[str, Any]:
        """Load validation rules"""
        if not self.rules_path.exists():
            logger.warning(f"Rules not found: {self.rules_path}, using empty rules")
            return {}
        
        with open(self.rules_path) as f:
            return json.load(f)

    def parse_log(self, raw_log: str, domain: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Parse raw log entry
        
        Returns:
            Tuple of (success, parsed_data, error_message)
        """
        try:
            # Parse based on domain
            if domain == "core_api":
                return self._parse_core_api(raw_log)
            elif domain == "llm":
                return self._parse_llm(raw_log)
            elif domain == "agentic":
                return self._parse_agentic(raw_log)
            elif domain == "cv":
                return self._parse_cv(raw_log)
            else:
                return False, None, f"Unknown domain: {domain}"
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return False, None, str(e)

    def _parse_core_api(self, raw_log: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Parse Core/API logs"""
        try:
            data = json.loads(raw_log)
            if not data.get("timestamp") or not data.get("endpoint"):
                return False, None, "Missing required fields: timestamp, endpoint"
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, f"JSON decode error: {e}"

    def _parse_llm(self, raw_log: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Parse LLM logs"""
        try:
            data = json.loads(raw_log)
            if not data.get("model") or not data.get("prompt"):
                return False, None, "Missing required fields: model, prompt"
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, f"JSON decode error: {e}"

    def _parse_agentic(self, raw_log: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Parse Agentic logs"""
        try:
            data = json.loads(raw_log)
            if not data.get("agent_id") or not data.get("action"):
                return False, None, "Missing required fields: agent_id, action"
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, f"JSON decode error: {e}"

    def _parse_cv(self, raw_log: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Parse Computer Vision logs"""
        try:
            data = json.loads(raw_log)
            if not data.get("image_id") or not data.get("task"):
                return False, None, "Missing required fields: image_id, task"
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, f"JSON decode error: {e}"

    def validate_schema(self, data: Dict, domain: str) -> Tuple[bool, Optional[str]]:
        """Validate parsed data against schema"""
        try:
            schema = self.load_schema(domain)
            # Basic schema validation
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            return True, None
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False, str(e)

    def classify_log(self, data: Dict, domain: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Classify log entry"""
        try:
            classification = {
                "domain": domain,
                "confidence": 0.95,  # Placeholder
                "category": self._get_category(data, domain)
            }
            return True, None, classification
        except Exception as e:
            return False, str(e), None

    @staticmethod
    def _get_category(data: Dict, domain: str) -> str:
        """Determine log category based on domain"""
        if domain == "core_api":
            return data.get("method", "GET").upper()
        elif domain == "llm":
            return data.get("model", "unknown")
        elif domain == "agentic":
            return data.get("action", "unknown")
        elif domain == "cv":
            return data.get("task", "unknown")
        return "unknown"

    def annotate_log(self, data: Dict, classification: Dict) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Add annotations to log"""
        try:
            annotation = {
                "timestamp": datetime.utcnow().isoformat(),
                "classification": classification,
                "tags": self._generate_tags(data, classification),
                "severity": self._determine_severity(data)
            }
            return True, None, annotation
        except Exception as e:
            return False, str(e), None

    @staticmethod
    def _generate_tags(data: Dict, classification: Dict) -> List[str]:
        """Generate tags for log"""
        tags = [classification.get("domain", "unknown")]
        if data.get("error"):
            tags.append("error")
        if data.get("warning"):
            tags.append("warning")
        return tags

    @staticmethod
    def _determine_severity(data: Dict) -> str:
        """Determine log severity"""
        if data.get("error"):
            return "ERROR"
        if data.get("warning"):
            return "WARNING"
        return "INFO"

    def validate_domain(self, domain: str, logs: List[str]) -> DomainMetrics:
        """
        Validate logs for a specific domain
        
        Args:
            domain: Domain name (core_api, llm, agentic, cv)
            logs: List of raw log strings
        
        Returns:
            DomainMetrics with results
        """
        metrics = DomainMetrics(
            domain=domain,
            total_logs=len(logs),
            parse_ok=0,
            parse_failed=0,
            schema_violation=0,
            classification_ok=0,
            classification_failed=0,
            annotation_ok=0,
            annotation_failed=0
        )

        for raw_log in logs:
            # Step 1: Parse
            parse_ok, parsed_data, parse_error = self.parse_log(raw_log, domain)
            if not parse_ok:
                metrics.parse_failed += 1
                logger.warning(f"Parse failed: {parse_error}")
                continue
            
            metrics.parse_ok += 1

            # Step 2: Validate Schema
            schema_ok, schema_error = self.validate_schema(parsed_data, domain)
            if not schema_ok:
                metrics.schema_violation += 1
                logger.warning(f"Schema violation: {schema_error}")
                continue

            # Step 3: Classify
            classify_ok, classify_error, classification = self.classify_log(parsed_data, domain)
            if not classify_ok:
                metrics.classification_failed += 1
                logger.warning(f"Classification failed: {classify_error}")
                continue
            
            metrics.classification_ok += 1

            # Step 4: Annotate
            annotate_ok, annotate_error, annotation = self.annotate_log(parsed_data, classification)
            if not annotate_ok:
                metrics.annotation_failed += 1
                logger.warning(f"Annotation failed: {annotate_error}")
                continue
            
            metrics.annotation_ok += 1

        metrics.calculate_rates()
        return metrics

    def run_validation(self, test_data: Dict[str, List[str]]) -> ValidationReport:
        """
        Run complete E2E validation
        
        Args:
            test_data: Dict mapping domain names to lists of raw logs
        
        Returns:
            ValidationReport with results
        """
        logger.info("Starting E2E validation...")
        
        domains_metrics = {}
        total_logs = 0
        total_parse_ok = 0
        total_failed = 0

        for domain, logs in test_data.items():
            logger.info(f"Validating domain: {domain} ({len(logs)} logs)")
            metrics = self.validate_domain(domain, logs)
            domains_metrics[domain] = metrics
            
            total_logs += metrics.total_logs
            total_parse_ok += metrics.parse_ok
            total_failed += metrics.parse_failed + metrics.schema_violation

        report = ValidationReport(
            timestamp=datetime.utcnow().isoformat(),
            domains=domains_metrics,
            total_logs=total_logs,
            total_parse_ok=total_parse_ok,
            total_failed=total_failed
        )
        report.calculate_overall_rate()

        logger.info("E2E validation completed")
        return report

    def generate_json_report(self, report: ValidationReport, output_path: Path) -> None:
        """Generate JSON report"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report_data = {
            "timestamp": report.timestamp,
            "summary": {
                "total_logs": report.total_logs,
                "total_parse_ok": report.total_parse_ok,
                "total_failed": report.total_failed,
                "overall_success_rate": report.overall_success_rate
            },
            "domains": {
                domain: asdict(metrics)
                for domain, metrics in report.domains.items()
            }
        }
        
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"JSON report written to: {output_path}")

    def generate_junit_report(self, report: ValidationReport, output_path: Path) -> None:
        """Generate JUnit XML report"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<testsuites>',
        ]
        
        for domain, metrics in report.domains.items():
            total_tests = metrics.total_logs
            failures = metrics.parse_failed + metrics.schema_violation + metrics.classification_failed
            
            xml_lines.extend([
                f'  <testsuite name="e2e_validation.{domain}" tests="{total_tests}" failures="{failures}">',
                f'    <property name="parse_rate" value="{metrics.parse_rate:.2f}%"/>',
                f'    <property name="schema_valid_rate" value="{metrics.schema_valid_rate:.2f}%"/>',
                f'    <property name="classification_rate" value="{metrics.classification_rate:.2f}%"/>',
                f'    <property name="annotation_rate" value="{metrics.annotation_rate:.2f}%"/>',
            ])
            
            if failures > 0:
                xml_lines.append(
                    f'    <failure message="{failures} validation failures in {domain}"/>'
                )
            
            xml_lines.append('  </testsuite>')
        
        xml_lines.append('</testsuites>')
        
        with open(output_path, "w") as f:
            f.write("\n".join(xml_lines))
        
        logger.info(f"JUnit report written to: {output_path}")

    def print_report(self, report: ValidationReport) -> None:
        """Print human-readable report"""
        print("\n" + "="*80)
        print("E2E VALIDATION REPORT")
        print("="*80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Overall Success Rate: {report.overall_success_rate:.2f}%")
        print(f"Total Logs: {report.total_logs}")
        print(f"Parse OK: {report.total_parse_ok}")
        print(f"Failed: {report.total_failed}")
        print()
        
        for domain, metrics in report.domains.items():
            print(f"\nDomain: {domain}")
            print(f"  Total Logs: {metrics.total_logs}")
            print(f"  Parse Rate: {metrics.parse_rate:.2f}%")
            print(f"  Schema Valid Rate: {metrics.schema_valid_rate:.2f}%")
            print(f"  Classification Rate: {metrics.classification_rate:.2f}%")
            print(f"  Annotation Rate: {metrics.annotation_rate:.2f}%")
        
        print("\n" + "="*80)
