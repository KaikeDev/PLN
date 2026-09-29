"""CLI: python -m app.classification build/verify."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Classificação de gêneros das sinopses com as representações da Etapa 2")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Validação cruzada multiclasse e multirrótulo para cada representação")
    build.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    build.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build.add_argument("--config", type=Path, required=True)
    verify = commands.add_parser("verify", help="Validar hashes e a cobertura dos arquivos de previsões")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            from app.classification.pipeline import build as build_classification

            print(json.dumps(build_classification(args.input, args.output, args.config), ensure_ascii=False))
        else:
            from app.classification.pipeline import verify as verify_classification

            print(json.dumps(verify_classification(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
