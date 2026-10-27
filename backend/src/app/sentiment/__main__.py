"""CLI: python -m app.sentiment collect / process / build / verify / llm-sample / llm-eval / llm-verify.

Os três últimos são o sentimento com LLM (ADR 0031): sortear a amostra, avaliar e conferir uma pasta avaliada.
"""

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
    sample = commands.add_parser("llm-sample", help="Sortear a amostra equilibrada do sentimento com LLM")
    sample.add_argument("--input", type=Path, required=True, help="Pasta preparada das críticas")
    sample.add_argument("--predictions", type=Path, required=True, help="Pasta do experimento com as predições fora da dobra")
    sample.add_argument("--config", type=Path, required=True, help="config/sentimento/sentimento_llm.json")
    sample.add_argument("--output", type=Path, required=True, help="Arquivo novo da amostra; nunca é sobrescrito")
    evaluate = commands.add_parser("llm-eval", help="Avaliar o LLM na amostra e comparar com o TF-IDF e o BERTimbau")
    evaluate.add_argument("--input", type=Path, required=True, help="Pasta preparada das críticas")
    evaluate.add_argument("--predictions", type=Path, required=True, help="Pasta do experimento com as predições fora da dobra")
    evaluate.add_argument("--config", type=Path, required=True, help="config/sentimento/sentimento_llm.json")
    evaluate.add_argument("--sample", type=Path, required=True, help="config/sentimento/sentimento_llm_amostra.json")
    evaluate.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    evaluate.add_argument("--reuse", type=Path, help="Pasta de uma execução anterior cujas respostas serão reaproveitadas")
    llm_verify = commands.add_parser("llm-verify", help="Validar hashes e alinhamento de uma avaliação do sentimento com LLM")
    llm_verify.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "llm-sample":
            from app.sentiment.llm.prompt import load_config as load_llm_config
            from app.sentiment.llm.sample import draw_sample, load_reviews
            from app.shared.artifacts import write_json

            if args.output.exists():
                raise FileExistsError(f"O arquivo da amostra já existe: {args.output}")
            drawn = draw_sample(load_reviews(args.input, args.predictions), load_llm_config(args.config).sample)
            write_json(args.output, drawn)
            print(json.dumps(drawn["estratos"], ensure_ascii=False))
        elif args.command == "llm-eval":
            print(json.dumps(run_llm_eval(args), ensure_ascii=False))
        elif args.command == "llm-verify":
            from app.sentiment.llm.pipeline import verify as verify_llm

            print(json.dumps(verify_llm(args.input), ensure_ascii=False))
        elif args.command == "collect":
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


def run_llm_eval(args: argparse.Namespace) -> dict:
    """Avaliação com os provedores de `config/llm/llm.json` e o TF-IDF da tela nos casos da equipe."""
    from app.llm.compose import provider_models
    from app.sentiment.live import SentimentAnalyzer
    from app.sentiment.llm.pipeline import Inputs, run
    from app.settings import get_settings

    settings = get_settings()
    inputs = Inputs(args.input, args.predictions, args.config, args.sample, settings.llm_config)

    def screen() -> SentimentAnalyzer:
        return SentimentAnalyzer.load(args.input, settings.sentiment_config, settings.sentiment_representation)

    return run(inputs, args.output, lambda: provider_models(settings)[0], args.reuse, screen)


if __name__ == "__main__":
    raise SystemExit(main())
