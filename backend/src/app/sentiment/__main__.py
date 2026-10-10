"""CLI: python -m app.sentiment collect / process / build / verify."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Análise de sentimentos de críticas do TMDB com as representações da Etapa 2")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="Coletar as críticas em português dos filmes de uma pasta processada")
    collect.add_argument("--movies", type=Path, required=True, help="Pasta processada da Etapa 1 com os filmes")
    collect.add_argument("--config", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    process = commands.add_parser("process", help="Filtrar as críticas e gerar as etapas de texto da Etapa 1, sem rede")
    process.add_argument("--input", type=Path, required=True, help="Pasta da coleta de críticas")
    process.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    process.add_argument("--stopwords", type=Path, required=True)
    build = commands.add_parser("build", help="Polaridade e nota previstas com validação cruzada para cada representação")
    build.add_argument("--input", type=Path, required=True, help="Pasta processada das críticas")
    build.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build.add_argument("--config", type=Path, required=True)
    verify = commands.add_parser("verify", help="Validar hashes de uma pasta de coleta, preparação ou experimento")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "collect":
            from app.sentiment.collect import collect as collect_reviews

            print(json.dumps(collect_reviews(args.movies, args.config, args.output), ensure_ascii=False))
        elif args.command == "process":
            from app.sentiment.process import process as process_reviews

            print(json.dumps(process_reviews(args.input, args.output, args.stopwords), ensure_ascii=False))
        elif args.command == "build":
            from app.sentiment.pipeline import build as build_sentiment

            print(json.dumps(build_sentiment(args.input, args.output, args.config), ensure_ascii=False))
        else:
            from app.sentiment.pipeline import verify_any

            print(json.dumps(verify_any(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
