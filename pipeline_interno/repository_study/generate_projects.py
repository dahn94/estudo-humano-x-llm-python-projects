from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath

import yaml
from dotenv import load_dotenv


def safe_files(raw: str) -> list[dict]:
    start, end = raw.find("{"), raw.rfind("}")
    payload = json.loads(raw[start : end + 1])
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Resposta sem lista de arquivos")
    validated = []
    for item in files:
        path = PurePosixPath(str(item["path"]))
        if path.is_absolute() or ".." in path.parts or not str(item.get("content", "")):
            raise ValueError(f"Caminho/conteúdo inválido: {path}")
        validated.append({"path": path, "content": str(item["content"])})
    return validated


def call(provider: str, model: str, prompt: str, max_tokens: int) -> str:
    if provider == "openai":
        from openai import OpenAI
        return OpenAI().responses.create(model=model, input=prompt, max_output_tokens=max_tokens).output_text
    if provider == "gemini":
        from google import genai
        from google.genai import types
        response = genai.Client(api_key=os.environ["GEMINI_API_KEY"]).models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=max_tokens, response_mime_type="application/json"),
        )
        return response.text or ""
    if provider == "claude":
        from anthropic import Anthropic
        response = Anthropic().messages.create(
            model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}],
        )
        return "\n".join(block.text for block in response.content if block.type == "text")
    raise ValueError(provider)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("openai", "gemini", "claude"), required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--study-config", default="repository_study/config.yaml")
    parser.add_argument("--generation-config", default="generation.yaml")
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit deve ser positivo")

    study = yaml.safe_load(Path(args.study_config).read_text(encoding="utf-8"))
    generation = yaml.safe_load(Path(args.generation_config).read_text(encoding="utf-8"))
    load_dotenv(generation["secrets_file"])
    provider_cfg = generation["providers"][args.provider]
    if not args.dry_run and not os.getenv(provider_cfg["api_key_env"]):
        raise SystemExit(f"Credencial ausente: {provider_cfg['api_key_env']}")
    prompts_path = Path(study["workspace"]) / "project_prompts.jsonl"
    prompts = [json.loads(line) for line in prompts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = prompts[args.start : args.start + args.limit]
    if args.dry_run:
        for item in selected:
            print(f"DRY RUN: {args.provider} -> {item['id']} ({len(item['prompt'])} chars)")
        return

    root = Path(study["workspace"]) / "generated" / args.provider
    manifest = Path(study["workspace"]) / "generation_manifest.jsonl"
    for item in selected:
        target = root / item["id"]
        if target.exists() and any(target.iterdir()) and not args.overwrite:
            print(f"[PULAR] {item['id']}")
            continue
        try:
            raw = call(args.provider, provider_cfg["model"], item["prompt"], generation["generation"]["max_output_tokens"])
            files = safe_files(raw)
            for file in files:
                destination = target.joinpath(*file["path"].parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(file["content"], encoding="utf-8")
            record = {"id": item["id"], "repo": item["repo"], "provider": args.provider, "model": provider_cfg["model"], "status": "generated", "files": len(files), "path": target.as_posix()}
        except Exception as exc:
            record = {"id": item["id"], "repo": item["repo"], "provider": args.provider, "model": provider_cfg["model"], "status": "error", "error": f"{type(exc).__name__}: {exc}"}
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[{record['status'].upper()}] {item['id']}")


if __name__ == "__main__":
    main()
