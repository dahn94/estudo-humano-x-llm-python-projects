from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROVIDERS = {"openai", "gemini", "claude"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa respostas JSONL produzidas por colaboradores.")
    parser.add_argument("input", help="JSONL com id, provider, model e generated_code")
    parser.add_argument("--config", default="generation.yaml")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    generated_root = Path(cfg["generated_root"])
    manifest = generated_root / "generations.jsonl"
    valid_ids = {
        json.loads(line)["id"]
        for line in Path(cfg["prompts_file"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    imported = 0
    with Path(args.input).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            missing = {"id", "provider", "model", "generated_code"} - item.keys()
            if missing:
                raise SystemExit(f"Linha {line_number}: campos ausentes: {sorted(missing)}")
            if item["id"] not in valid_ids:
                raise SystemExit(f"Linha {line_number}: id desconhecido: {item['id']}")
            if item["provider"] not in PROVIDERS:
                raise SystemExit(f"Linha {line_number}: provider inválido: {item['provider']}")

            provider_root = generated_root / item["provider"]
            provider_root.mkdir(parents=True, exist_ok=True)
            code_path = provider_root / f"{item['id']}.py"
            if code_path.exists() and not args.overwrite:
                print(f"[PULAR] {item['provider']}/{item['id']} já existe")
                continue
            code = str(item["generated_code"]).strip() + "\n"
            code_path.write_text(code, encoding="utf-8")
            record = {
                "sample_id": item["id"], "provider": item["provider"],
                "model": item["model"], "status": "imported",
                "code_path": code_path.as_posix(), "generated_code": code,
                "error": "", "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            manifest.parent.mkdir(parents=True, exist_ok=True)
            with manifest.open("a", encoding="utf-8") as target:
                target.write(json.dumps(record, ensure_ascii=False) + "\n")
            imported += 1
    print(f"Importadas: {imported} resposta(s)")


if __name__ == "__main__":
    main()
