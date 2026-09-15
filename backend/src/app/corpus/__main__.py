"""CLI da Etapa 1: `python -m app.corpus collect | process | verify`.

`collect` devolve código 0 quando a coleta termina completa e 2 quando é parcial; erros de entrada
também terminam com código 2 e mensagem, sem traceback.
"""

import argparse
import json
from pathlib import Path

COLLECT_SUMMARY_FIELDS = ("status", "unique_movies", "records_received", "duplicates_removed")


def build_parser() -> argparse.ArgumentParser:
    """Parser com os subcomandos da Etapa 1."""
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
    return parser


def main() -> int:
    """Executa o subcomando pedido e imprime o resultado em JSON."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "collect":
            from app.corpus.collect import collect

            result = collect(args.config, args.output)
            print(json.dumps({key: result[key] for key in COLLECT_SUMMARY_FIELDS}, ensure_ascii=False))
            return 0 if result["status"] == "complete" else 2
        if args.command == "process":
            from app.corpus.process import process

            print(json.dumps(process(args.input, args.output, args.stopwords), ensure_ascii=False))
            return 0
        from app.corpus.verification import verify_processed

        print(json.dumps(verify_processed(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
