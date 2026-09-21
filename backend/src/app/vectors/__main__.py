"""CLI: python -m app.vectors build/verify/query."""

import argparse
import json
from pathlib import Path


def bounded_k(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 50:
        raise argparse.ArgumentTypeError("k deve estar entre 1 e 50")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Representações vetoriais das sinopses processadas (BoW, TF-IDF, word2vec, BERT e embeddings de sentença)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Gerar matrizes, similaridade, clustering, projeção e avaliação de consultas")
    build.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    build.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--queries", type=Path, help="Consultas anotadas (opcional)")
    build.add_argument("--probes", type=Path, help="Sondas linguísticas: pares de frases, pares de palavras e polissemia (opcional)")
    verify = commands.add_parser("verify", help="Validar hashes e alinhamento das matrizes")
    verify.add_argument("--input", type=Path, required=True)
    query = commands.add_parser("query", help="Buscar sinopses por uma consulta em linguagem natural")
    query.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    query.add_argument("--config", type=Path, required=True)
    query.add_argument("--representation", required=True)
    query.add_argument("--text", required=True)
    query.add_argument("--k", type=bounded_k, default=5)
    args = parser.parse_args()
    try:
        if args.command == "build":
            from app.vectors.pipeline import build as build_vectors

            print(json.dumps(build_vectors(args.input, args.output, args.config, args.queries, args.probes), ensure_ascii=False))
        elif args.command == "verify":
            from app.vectors.pipeline import verify as verify_vectors

            print(json.dumps(verify_vectors(args.input), ensure_ascii=False))
        else:
            from app.vectors.pipeline import build_one
            from app.vectors.retrieval import search

            corpus, representation = build_one(args.input, args.config, args.representation)
            result = search(representation, corpus, args.text)
            print(
                json.dumps(
                    {
                        "representation": args.representation,
                        "tokens": result.query.tokens,
                        "out_of_vocabulary": result.query.out_of_vocabulary,
                        "null_vector": result.query.null,
                        "results": result.top(corpus, args.k),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
