def _load_schemas(self):
    """Load all domain schemas and shared defs into the registry and build validators."""
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    registry_resources = []

    # 1) Load ALL .schema.json files (versioned + top-level wrappers)
    for schema_file in self._schema_dir.rglob("*.schema.json"):
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_content = json.load(f)
        schema_id = schema_content.get("$id")
        if schema_id:
            registry_resources.append((schema_id, Resource.from_contents(schema_content, default_specification=DRAFT202012)))

    # 2) ALSO load shared/common vocab (not *.schema.json), e.g. _common.json
    common_path = self._schema_dir / "_common.json"
    if common_path.exists():
        with open(common_path, "r", encoding="utf-8") as f:
            common_schema = json.load(f)
        common_id = common_schema.get("$id")
        if common_id:
            registry_resources.append((common_id, Resource.from_contents(common_schema, default_specification=DRAFT202012)))

    # (Optional) If you have other shared files, add them here the same way.

    # 3) Build a registry with everything
    registry = Registry().with_resources(registry_resources)

    # 4) Cache and prepare per-domain validators
    domains = ["core_api", "llm", "agentic", "cv"]
    for domain in domains:
        schema_path = self._schema_dir / f"{domain}.schema.json"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            self._schema_cache[domain] = schema
            self._validators[domain] = Draft202012Validator(schema, registry=registry)
