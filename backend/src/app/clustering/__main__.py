"""CLI: python -m app.clustering sweep / verify (o agrupamento com k fixo roda em `app.representations build`)."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Varredura do número de clusters do K-Means para cada representação")
    commands = parser.add_subparsers(dest="command", required=True)
    sweep = commands.add_parser("sweep", help="Métricas intra e intercluster e contra os gêneros para cada k")
    sweep.add_argument("--input", type=Path, required=True, help="Pasta processada da Etapa 1")
    sweep.add_argument("--vectors-config", type=Path, required=True, help="Configuração das representações (vetorizacao*.json)")
    sweep.add_argument("--vectors", type=Path, help="Pasta verificada da Etapa 2; os vetores densos são lidos dela (opcional)")
    sweep.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    sweep.add_argument("--config", type=Path, required=True)
    verify = commands.add_parser("verify", help="Validar os hashes de uma varredura")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        from app.clustering.sweep import sweep as run_sweep
        from app.clustering.sweep import verify as verify_sweep

        if args.command == "sweep":
            print(json.dumps(run_sweep(args.input, args.vectors_config, args.output, args.config, args.vectors), ensure_ascii=False))
        else:
            print(json.dumps(verify_sweep(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
