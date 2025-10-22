from pathlib import Path
import json
from jsonschema import Draft202012Validator, RefResolver


class SchemaValidator:
    def __init__(self):
        self._schema_cache = {}
        self._validators = {}

        self._schema_dir = (Path(__file__).resolve().parents[3] / "schemas").resolve()

        # Build local ref store for all JSON files, including _common.json
        self._store = {}
        for jf in self._schema_dir.rglob("*.json"):
            try:
                uri = jf.resolve().as_uri()
                self._store[uri] = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                pass

        # ensure _common.json is explicitly indexed
        common_path = (self._schema_dir / "_common.json").resolve()
        if common_path.exists():
            self._store[common_path.as_uri()] = json.loads(common_path.read_text(encoding="utf-8"))

        self._load_domain_validators()

    def _load_domain_validators(self):
        for domain in ("core_api", "llm", "agentic", "cv"):
            schema_path = (self._schema_dir / f"{domain}.schema.json").resolve()
            if not schema_path.exists():
                continue

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            resolver = RefResolver(
                base_uri=schema_path.as_uri(),
                referrer=schema,
                store=self._store,
            )
            self._schema_cache[domain] = schema
            self._validators[domain] = Draft202012Validator(schema, resolver=resolver)
