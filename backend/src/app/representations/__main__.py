"""CLI: python -m app.representations build/verify."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Representações vetoriais das sinopses processadas (BoW, TF-IDF, word2vec, BERT e embeddings de sentença)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Gerar as representações e rodar busca, recomendação, agrupamento, visualização e sondas")
    build.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    build.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--queries", type=Path, help="Consultas anotadas (opcional)")
    build.add_argument("--probes", type=Path, help="Sondas linguísticas: pares de frases, pares de palavras e polissemia (opcional)")
    verify = commands.add_parser("verify", help="Validar hashes e alinhamento das matrizes")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            from app.representations.pipeline import build as build_vectors

            print(json.dumps(build_vectors(args.input, args.output, args.config, args.queries, args.probes), ensure_ascii=False))
        else:
            from app.representations.pipeline import verify as verify_vectors

            print(json.dumps(verify_vectors(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
