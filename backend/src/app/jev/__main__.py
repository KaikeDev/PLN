"""CLI: python -m app.jev run/verify."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classificação de gênero das sinopses com o Jev (TypeSafe AI) comparada a TF-IDF + regressão logística"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Chamar o Jev na amostra, treinar a referência e gerar métricas e relatório")
    run.add_argument("--input", type=Path, required=True, help="Pasta processada pela Etapa 1")
    run.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--reuse", type=Path, help="Pasta de uma execução anterior cujas respostas serão reaproveitadas sem novas chamadas")
    verify = commands.add_parser("verify", help="Validar hashes e alinhamento das respostas e previsões")
    verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            from app.infra.typesafe.client import TypeSafeDecisionClient
            from app.jev.pipeline import run as run_jev
            from app.settings import get_settings

            def client_factory() -> TypeSafeDecisionClient:
                return TypeSafeDecisionClient(get_settings().require_typesafe_key())

            print(json.dumps(run_jev(args.input, args.output, args.config, client_factory, args.reuse), ensure_ascii=False))
        else:
            from app.jev.pipeline import verify as verify_jev

            print(json.dumps(verify_jev(args.input), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
