from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml
from dotenv import load_dotenv


@dataclass
class GenerationResult:
    sample_id: str
    provider: str
    model: str
    status: str
    code_path: str
    generated_code: str
    error: str
    generated_at: str


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def extract_python(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.I | re.S)
    return (match.group(1) if match else text).strip() + "\n"


def call_openai(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    from openai import OpenAI

    response = OpenAI().responses.create(
        model=model,
        input=prompt,
        max_output_tokens=max_tokens,
    )
    return response.output_text


def call_gemini(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text or ""


def call_claude(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    from anthropic import Anthropic

    response = Anthropic().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return "\n".join(block.text for block in response.content if block.type == "text")


CALLERS: dict[str, Callable[[str, str, int, float], str]] = {
    "openai": call_openai,
    "gemini": call_gemini,
    "claude": call_claude,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera implementações a partir de prompts JSONL.")
    parser.add_argument("--provider", choices=sorted(CALLERS), required=True)
    parser.add_argument("--limit", type=int, required=True, help="Máximo de prompts nesta execução.")
    parser.add_argument("--start", type=int, default=0, help="Índice inicial, começando em zero.")
    parser.add_argument("--config", default="generation.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit deve ser maior que zero")

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    secrets_path = Path(cfg["secrets_file"])
    if secrets_path.exists():
        load_dotenv(secrets_path)

    provider_cfg = cfg["providers"][args.provider]
    key_name = provider_cfg["api_key_env"]
    if not args.dry_run and not os.getenv(key_name):
        raise SystemExit(f"Configure {key_name} em {secrets_path} antes de executar.")

    prompts = read_jsonl(Path(cfg["prompts_file"]))
    selected = prompts[args.start : args.start + args.limit]
    generated_root = Path(cfg["generated_root"])
    provider_root = generated_root / args.provider
    manifest = generated_root / "generations.jsonl"
    provider_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(f"DRY RUN: {len(selected)} prompt(s), provedor={args.provider}, modelo={provider_cfg['model']}")
        for item in selected:
            print(f"- {item['id']}: {item['repo']} | {item['qualified_name']}")
        return

    gen_cfg = cfg["generation"]
    for item in selected:
        output_path = provider_root / f"{item['id']}.py"
        if output_path.exists() and not args.overwrite:
            print(f"[PULAR] {item['id']} já existe")
            continue

        error = ""
        code = ""
        status = "error"
        for attempt in range(1, int(gen_cfg["retries"]) + 1):
            try:
                raw = CALLERS[args.provider](
                    provider_cfg["model"],
                    item["prompt"],
                    int(gen_cfg["max_output_tokens"]),
                    float(gen_cfg["temperature"]),
                )
                code = extract_python(raw)
                output_path.write_text(code, encoding="utf-8")
                status = "generated"
                break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                if attempt < int(gen_cfg["retries"]):
                    time.sleep(float(gen_cfg["retry_delay_seconds"]) * attempt)

        result = GenerationResult(
            sample_id=item["id"], provider=args.provider, model=provider_cfg["model"],
            status=status, code_path=output_path.as_posix() if code else "",
            generated_code=code, error=error,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        append_jsonl(manifest, result.__dict__)
        print(f"[{status.upper()}] {item['id']}")


if __name__ == "__main__":
    main()
