"""CLI: python -m app.entities credits / build / verify."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Entidades nomeadas e relações nas sinopses com o spaCy (Aula 9)")
    commands = parser.add_subparsers(dest="command", required=True)
    credits = commands.add_parser("credits", help="Coletar o elenco dos filmes de uma pasta processada, como referência do NER")
    credits.add_argument("--movies", type=Path, required=True, help="Pasta processada da Etapa 1")
    credits.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build = commands.add_parser("build", help="Entidades, relações, conferência com os créditos e relatório")
    build.add_argument("--input", type=Path, required=True, help="Pasta processada da Etapa 1")
    build.add_argument("--credits", type=Path, required=True, help="Pasta da coleta de créditos")
    build.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build.add_argument("--config", type=Path, required=True)
    verify = commands.add_parser("verify", help="Validar hashes e alinhamento de uma pasta de resultados ou de créditos")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "credits":
            from app.entities.credits import collect_credits

            print(json.dumps(collect_credits(args.movies, args.output), ensure_ascii=False))
        elif args.command == "build":
            from app.entities.pipeline import build as build_entities

            print(json.dumps(build_entities(args.input, args.credits, args.output, args.config), ensure_ascii=False))
        else:
            from app.entities.credits import verify_credits
            from app.entities.pipeline import verify as verify_entities

            check = verify_credits if (args.input / "credits.jsonl").exists() else verify_entities
            print(json.dumps(check(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
