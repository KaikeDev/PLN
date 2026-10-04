"""CLI: python -m app.search query/hybrid.

- `query`: busca uma frase com uma única representação.
- `hybrid`: a combinação usada pelo site (`config/busca/busca.json`); com `--queries`, compara cada
  representação com a combinação nas consultas anotadas.
"""

import argparse
import json
from pathlib import Path


def bounded_k(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 50:
        raise argparse.ArgumentTypeError("k deve estar entre 1 e 50")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca de sinopses por uma consulta em linguagem natural")
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("query", help="Buscar sinopses por uma consulta em linguagem natural")
    query.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    query.add_argument("--config", type=Path, required=True)
    query.add_argument("--representation", required=True)
    query.add_argument("--text", required=True)
    query.add_argument("--k", type=bounded_k, default=5)
    hybrid = commands.add_parser("hybrid", help="Busca híbrida: avaliar a combinação nas consultas anotadas ou buscar uma frase")
    hybrid.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    hybrid.add_argument("--config", type=Path, required=True, help="Configuração vetorial com as representações combinadas")
    hybrid.add_argument("--search", type=Path, required=True, help="Pesos da busca (config/busca/busca.json)")
    target = hybrid.add_mutually_exclusive_group(required=True)
    target.add_argument("--queries", type=Path, help="Consultas anotadas: compara cada representação com a combinação")
    target.add_argument("--text", help="Frase a buscar")
    hybrid.add_argument("--k", type=bounded_k, default=5)
    args = parser.parse_args()
    try:
        if args.command == "hybrid":
            from app.representations.config import load_queries
            from app.search.hybrid import HybridIndex, evaluate, load_search_config

            index = HybridIndex.build(args.input, args.config, load_search_config(args.search))
            if args.queries:
                print(json.dumps(evaluate(index, load_queries(args.queries), args.k), ensure_ascii=False, indent=2))
            else:
                ranked = index.rank(args.text)[: args.k]
                top = [
                    {"id": movie_id, "title": index.corpus.by_id[movie_id].title, "score": round(score, 4)} for movie_id, score in ranked
                ]
                print(json.dumps(top, ensure_ascii=False, indent=2))
        else:
            from app.representations.pipeline import build_one
            from app.search.retrieval import search

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
