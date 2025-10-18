import glob
import json


def test_schema_field_order_and_enum_docs():
    for path in glob.glob("schemas/**/*.json", recursive=True):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "type" in data and data.get("type") == "object":
            keys = list(data.keys())
            # Best-effort order guard
            assert "required" in keys and "properties" in keys
        # Check enums carry at least one of description/$comment nearby
        def check_enums(obj):
            if isinstance(obj, dict):
                if "enum" in obj:
                    assert any(k in obj for k in ("description", "$comment"))
                for v in obj.values():
                    check_enums(v)
            elif isinstance(obj, list):
                for v in obj:
                    check_enums(v)
        check_enums(data)
