"""CLI: python -m app.corpus collect/process/verify."""
import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta e transformações rastreáveis para a Etapa Prática 1")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="Salvar uma nova amostra real do TMDB")
    collect.add_argument("--config", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    process = commands.add_parser("process", help="Processar amostra local sem rede")
    process.add_argument("--input", type=Path, required=True)
    process.add_argument("--output", type=Path, required=True)
    process.add_argument("--stopwords", type=Path, required=True)
    verify = commands.add_parser("verify", help="Validar integridade e alinhamento das representações")
    verify.add_argument("--input", type=Path, required=True)
    bow = commands.add_parser("bow", help="Gerar representação numérica Bag of Words")
    bow.add_argument("--input", type=Path, required=True)
    bow.add_argument("--output", type=Path, required=False)
    args = parser.parse_args()
    try:
        if args.command == "collect":
            from app.corpus.collect import collect as run
            result = run(args.config, args.output)
            print(json.dumps({key: result[key] for key in ["status", "unique_movies", "records_received", "duplicates_removed"]}, ensure_ascii=False))
            return 0 if result["status"] == "complete" else 2
        elif args.command == "process":
            from app.corpus.process import process as run
            print(json.dumps(run(args.input, args.output, args.stopwords), ensure_ascii=False))
        elif args.command == "bow":
            from app.corpus.bow import generate_bow_dataset
            from app.corpus.io import write_json
            res = generate_bow_dataset(args.input)
            if args.output:
                write_json(args.output, res)
            print(json.dumps({
                "total_documents": res["total_documents"],
                "vocabulary_size": res["vocabulary_size"],
                "sparsity_percent": res["sparsity_percent"],
                "top_5_terms": res["top_20_terms"][:5],
                "output": str(args.output) if args.output else "stdout",
            }, ensure_ascii=False, indent=2))
        else:
            from app.corpus.process import verify as run
            print(json.dumps(run(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
