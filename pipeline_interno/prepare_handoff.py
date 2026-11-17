from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria pacote sem segredos e sem código humano.")
    parser.add_argument("--provider", choices=("openai", "gemini", "claude", "all"), default="all")
    args = parser.parse_args()
    root = Path("workspace/handoff")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2("workspace/output/prompts.jsonl", root / "prompts.jsonl")
    shutil.copy2("secrets/providers.env.example", root / "providers.env.example")
    instructions = {
        "provider": args.provider,
        "contains_secrets": False,
        "contains_human_code": False,
        "instructions": "Use prompts.jsonl e devolva um objeto por linha com id, provider, model e generated_code.",
        "response_example": {"id": "sample_00001", "provider": "gemini", "model": "nome-do-modelo", "generated_code": "def exemplo():\n    pass"},
    }
    (root / "INSTRUCOES.json").write_text(json.dumps(instructions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pacote criado em {root.resolve()}")


if __name__ == "__main__":
    main()
