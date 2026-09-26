from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

DATA = Path(__file__).resolve().parents[1]
REPO = DATA.parent
RAW = DATA / "raw"
OUT = DATA / "out"
CONFIG = DATA / "config"
SAMPLE = DATA / "sample"
WEB_DATA = REPO / "web" / "public" / "data"

load_dotenv(REPO / ".env")


def require_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"API 키가 필요합니다: {name} (.env.example 참고)", file=sys.stderr)
        sys.exit(2)
    return value


def load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG / name).read_text(encoding="utf-8"))


def origin_config(origin_id: str | None = None) -> dict:
    cfg = load_yaml("origins.yaml")
    oid = origin_id or cfg["default"]
    return {"id": oid, **cfg["origins"][oid]}


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
