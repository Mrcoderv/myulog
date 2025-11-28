import json
from typing import Dict, Iterable


def get_record_id(rec: Dict) -> str:
    if not rec:
        return ""
    return rec.get("id") or rec.get("record_id") or ""


def load_jsonl(path: str) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                # skip invalid lines
                continue


def save_jsonl(path: str, records: Iterable[Dict]):
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
