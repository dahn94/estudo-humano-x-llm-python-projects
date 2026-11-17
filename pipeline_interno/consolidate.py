from __future__ import annotations

import csv
import json
from pathlib import Path


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    output_root = Path("workspace/output")
    prompts = jsonl(output_root / "prompts.jsonl")
    generations = jsonl(Path("workspace/generated/generations.jsonl"))
    analyses = jsonl(Path("workspace/analysis/analysis.jsonl"))

    latest_generation = {(x["sample_id"], x["provider"]): x for x in generations}
    latest_analysis = {(x["sample_id"], x["provider"]): x for x in analyses}
    providers = ("openai", "gemini", "claude")
    rows = []
    for prompt in prompts:
        row = {k: prompt.get(k, "") for k in ("id", "repo", "commit_sha", "file", "qualified_name", "prompt")}
        for provider in providers:
            gen = latest_generation.get((prompt["id"], provider), {})
            ana = latest_analysis.get((prompt["id"], provider), {})
            row.update({
                f"{provider}_model": gen.get("model", ""),
                f"{provider}_status": gen.get("status", "pending"),
                f"{provider}_code_path": gen.get("code_path", ""),
                f"{provider}_generated_code": gen.get("generated_code", ""),
                f"{provider}_error": gen.get("error", ""),
                f"{provider}_syntax_status": ana.get("syntax_status", "pending"),
                f"{provider}_test_status": ana.get("test_status", "pending"),
                f"{provider}_semgrep_status": ana.get("semgrep_status", "pending"),
                f"{provider}_semgrep_findings": ana.get("semgrep_findings", ""),
            })
        rows.append(row)

    destination = output_root / "resultado_comparativo.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Consolidado: {len(rows)} amostras em {destination.resolve()}")


if __name__ == "__main__":
    main()

