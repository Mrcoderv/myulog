def _load_schemas(self):
    """Load all domain schemas and build a local registry that resolves $refs."""

    # 1) Collect every *.schema.json as resources
    registry_resources = []
    for schema_file in self._schema_dir.rglob("*.schema.json"):
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_content = json.load(f)

        # If the schema declares an $id, register it under that URL
        if "$id" in schema_content:
            res = Resource.from_contents(schema_content, default_specification=DRAFT202012)
            registry_resources.append((schema_content["$id"], res))

        # Also register by absolute file URL so relative refs can resolve via file paths if needed
        file_url = schema_file.resolve().as_uri()
        res2 = Resource.from_contents(schema_content, default_specification=DRAFT202012)
        registry_resources.append((file_url, res2))

    # 2) Important: manually map the URL that relative refs point to
    # Example: ../../_common.json relative to $id "https://github.com/OmdenaAI/ULog/schemas/llm/v0/llm.schema.json"
    # becomes: "https://github.com/OmdenaAI/ULog/schemas/_common.json"
    common_file = (self._schema_dir / "_common.json").resolve()
    with open(common_file, "r", encoding="utf-8") as f:
        common_schema = json.load(f)

    common_url = "https://github.com/OmdenaAI/ULog/schemas/_common.json"
    registry_resources.append((common_url, Resource.from_contents(common_schema, default_specification=DRAFT202012)))
    registry = Registry().with_resources(registry_resources)

    # 3) Load top-level domain “wrapper” schemas (core_api.schema.json, llm.schema.json, etc.)
    domains = ["core_api", "llm", "agentic", "cv"]
    for domain in domains:
        schema_path = self._schema_dir / f"{domain}.schema.json"
        if not schema_path.exists():
            continue
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self._schema_cache[domain] = schema
        self._validators[domain] = Draft202012Validator(schema, registry=registry)
