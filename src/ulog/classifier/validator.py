class SchemaValidator:
    """Validates normalized logs against domain-specific JSON schemas."""

    def __init__(self):
    self._schema_cache = {}
    self._validators = {}
    self._schema_dir = Path(__file__).parent.parent.parent.parent / "schemas"
    self._registry = None  # set in _load_schemas()
    self._load_schemas()
    
    def _load_schemas(self):
    """Load all domain schemas from /schemas and build a registry with URL aliases."""
    registry_resources = []

    def add_resource(contents: dict, *keys: str):
        res = Resource.from_contents(contents, default_specification=DRAFT202012)
        for k in keys:
            registry_resources.append((k, res))

    # 1) Load every JSON that has a $id and register by:
    #    - its $id (verbatim)
    #    - its file:// absolute path
    #    - optional ulog.ai ↔ github.com alias (helps when refs mix both)
    for schema_file in self._schema_dir.rglob("*.json"):
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, dict) or "$id" not in data:
            continue

        sid = data["$id"]
        file_url = "file://" + schema_file.resolve().as_posix()

        alias_keys = {sid, file_url}

        # Add helpful domain aliases if present
        if sid.startswith("https://github.com/OmdenaAI/ULog/"):
            alias_keys.add(sid.replace("https://github.com/OmdenaAI/ULog", "https://ulog.ai"))
        if sid.startswith("https://ulog.ai/"):
            alias_keys.add(sid.replace("https://ulog.ai", "https://github.com/OmdenaAI/ULog"))

        add_resource(data, *alias_keys)

    # 2) Build registry
    registry = Registry().with_resources(registry_resources)
    self._registry = registry

    # 3) Load top-level domain wrappers and bind validators
    for domain in ("core_api", "llm", "agentic", "cv"):
        wrapper = self._schema_dir / f"{domain}.schema.json"
        if not wrapper.exists():
            continue
        with open(wrapper, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self._schema_cache[domain] = schema
        self._validators[domain] = Draft202012Validator(schema, registry=registry)
