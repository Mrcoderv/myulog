class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self):
        """Initialize validator with schema cache."""
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft202012Validator] = {}
        self._schema_dir = Path(__file__).parent.parent.parent.parent / "schemas"
        self._registry = None  # will be set in _load_schemas()
        self._load_schemas()

    def _load_schemas(self):
    """Load all domain schemas from the schemas directory and build a registry."""
    registry_resources = []

    # Load every JSON under /schemas that has a $id (includes _common.json and versioned files)
    for schema_file in self._schema_dir.rglob("*.json"):
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_content = json.load(f)
        except Exception:
            continue

        if isinstance(schema_content, dict) and "$id" in schema_content:
            res = Resource.from_contents(schema_content, default_specification=DRAFT202012)
            schema_id = schema_content["$id"]
            registry_resources.append((schema_id, res))

            # Also register a file:// alias to help with any file-based refs
            file_url = "file://" + schema_file.resolve().as_posix()
            registry_resources.append((file_url, res))

    registry = Registry().with_resources(registry_resources)
    self._registry = registry  # keep a handle if you want to introspect

    # Load the domain wrapper schemas (core_api.schema.json, llm.schema.json, etc.)
    domains = ["core_api", "llm", "agentic", "cv"]
    for domain in domains:
        schema_path = self._schema_dir / f"{domain}.schema.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self._schema_cache[domain] = schema
            self._validators[domain] = Draft202012Validator(schema, registry=registry)
     
