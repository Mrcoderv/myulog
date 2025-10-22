--- a/src/ulog/classifier/validator.py
+++ b/src/ulog/classifier/validator.py
@@ -1,14 +1,18 @@
-"""Schema validation module with helpful error envelopes."""
+"""Schema validation module with helpful error envelopes."""
 
 import json
 from pathlib import Path
 from typing import Any, Dict, Optional, Tuple
-from urllib.parse import urljoin
-from urllib.request import pathname2url
 
-import jsonschema
-from jsonschema import Draft202012Validator
-from referencing import Registry, Resource
-from referencing.jsonschema import DRAFT202012
+import jsonschema
+from jsonschema import Draft202012Validator, RefResolver
 
 
 class SchemaValidator:
     """Validates normalized logs against domain-specific JSON schemas."""
 
     def __init__(self):
         """Initialize validator with schema cache."""
         self._schema_cache: Dict[str, Dict[str, Any]] = {}
         self._validators: Dict[str, Draft202012Validator] = {}
-        self._schema_dir = Path(__file__).parent.parent.parent.parent / "schemas"
+        self._schema_dir = (Path(__file__).resolve().parents[3] / "schemas").resolve()
+        # a store of every *.json in schemas/ keyed by file:// URI for local ref resolution
+        self._store: Dict[str, Dict[str, Any]] = {}
         self._load_schemas()
 
     def _load_schemas(self):
         """Load all domain schemas from the schemas directory."""
-        # Build a registry for schema references
-        registry_resources = []
-
-        # Load all schemas recursively to build registry
-        for schema_file in self._schema_dir.rglob("*.schema.json"):
-            with open(schema_file, "r") as f:
-                schema_content = json.load(f)
-                if "$id" in schema_content:
-                    resource = Resource.from_contents(schema_content, default_specification=DRAFT202012)
-                    registry_resources.append((schema_content["$id"], resource))
-
-        # Create registry with all schemas
-        registry = Registry().with_resources(registry_resources)
+        # Index *every* json file under schemas/ by its file:// URI
+        for jf in self._schema_dir.rglob("*.json"):
+            try:
+                self._store[jf.resolve().as_uri()] = json.loads(jf.read_text(encoding="utf-8"))
+            except Exception:
+                # keep going; only well-formed JSON files will be usable
+                pass
 
         # Load domain schemas
         domains = ["core_api", "llm", "agentic", "cv"]
         for domain in domains:
             schema_path = self._schema_dir / f"{domain}.schema.json"
             if schema_path.exists():
-                with open(schema_path, "r") as f:
-                    schema = json.load(f)
-                    self._schema_cache[domain] = schema
-                    self._validators[domain] = Draft202012Validator(schema, registry=registry)
+                schema_path = schema_path.resolve()
+                schema = json.loads(schema_path.read_text(encoding="utf-8"))
+                self._schema_cache[domain] = schema
+                # Crucial: base_uri is the file:// of the domain schema.
+                # This makes "../../_common.json#/$defs/..." resolve locally.
+                resolver = RefResolver(
+                    base_uri=schema_path.as_uri(),
+                    referrer=schema,
+                    store=self._store,
+                )
+                self._validators[domain] = Draft202012Validator(schema, resolver=resolver)
 
     def validate(self, record: Dict[str, Any], domain: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
         """Validate a record against its domain schema.
@@ -111,5 +115,5 @@ class SchemaValidator:
         return envelope
 
     def get_available_domains(self) -> list:
         """Get list of available domain schemas.
 
         Returns:
-            List of domain names with loaded schemas
-        """
-        return list(self._schema_cache.keys())
+            List of domain names with loaded schemas
+        """
+        return list(self._schema_cache.keys())
