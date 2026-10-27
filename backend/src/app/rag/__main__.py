"""CLI: python -m app.rag eval / verify / judgment-template / agreement / export-examples.

- `eval`: avalia o RAG na amostra de 428 filmes (exige o extra `semantico` e as críticas preparadas). O prompt da
  interpretação, os gêneros, as pastas da amostra e a configuração do LLM vêm de `app.settings`.
- `verify`: confere uma pasta de avaliação.
- `judgment-template`: escreve o arquivo que os dois juízes preenchem (fora da pasta da avaliação, que é imutável).
- `agreement`: concordância e kappa de Cohen dos julgamentos preenchidos.
- `export-examples`: grava as respostas escolhidas de uma avaliação como exemplos do site (`frontend/dados/exemplos_rag.json`).
"""

import argparse
import json
from pathlib import Path

DEFAULT_EXAMPLES = ("tema_luto", "tema_zumbis_comedia", "tema_prisao", "opiniao_oppenheimer", "opiniao_barbie", "sem_curling")


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG: perguntas sobre os filmes com respostas citadas")
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate = commands.add_parser("eval", help="Avaliar o RAG na amostra")
    evaluate.add_argument("--questions", type=Path, required=True, help="config/rag/perguntas.json")
    evaluate.add_argument("--queries", type=Path, required=True, help="config/busca/consultas.json")
    evaluate.add_argument("--config", type=Path, required=True, help="config/rag/rag.json")
    evaluate.add_argument("--output", type=Path, required=True, help="Pasta nova; nunca é sobrescrita")
    evaluate.add_argument("--reuse", type=Path, help="Pasta de uma execução anterior cujas respostas serão reaproveitadas")
    evaluate.add_argument("--without-ablation", action="store_true", help="Não repetir as perguntas sem trechos de crítica")
    verify = commands.add_parser("verify", help="Validar hashes e alinhamento de uma avaliação")
    verify.add_argument("--input", type=Path, required=True)
    template = commands.add_parser("judgment-template", help="Escrever o arquivo de julgamentos para os juízes")
    template.add_argument("--input", type=Path, required=True, help="Pasta da avaliação")
    template.add_argument("--output", type=Path, required=True, help="Arquivo novo; nunca é sobrescrito")
    agreement = commands.add_parser("agreement", help="Concordância entre os juízes")
    agreement.add_argument("--input", type=Path, required=True, help="Pasta da avaliação")
    agreement.add_argument("--judgments", type=Path, required=True)
    examples = commands.add_parser("export-examples", help="Gravar respostas da avaliação como exemplos do site")
    examples.add_argument("--input", type=Path, required=True, help="Pasta da avaliação")
    examples.add_argument("--output", type=Path, required=True, help="frontend/dados/exemplos_rag.json")
    examples.add_argument("--ids", nargs="+", default=list(DEFAULT_EXAMPLES))
    args = parser.parse_args()
    try:
        if args.command == "eval":
            result = run_eval(args)
        elif args.command == "verify":
            from app.rag.pipeline import verify as verify_rag

            result = verify_rag(args.input)
        elif args.command == "judgment-template":
            from app.rag.pipeline import judgment_template
            from app.shared.artifacts import write_json

            if args.output.exists():
                raise FileExistsError(f"O arquivo já existe: {args.output}")
            write_json(args.output, judgment_template(args.input))
            result = {"output": str(args.output)}
        elif args.command == "agreement":
            from app.rag.pipeline import judgment_agreement

            result = judgment_agreement(args.input, args.judgments)
        else:
            from app.rag.examples import export_examples
            from app.settings import get_settings

            result = export_examples(args.input, get_settings().sample_raw_dir / "movies.jsonl", args.output, args.ids)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"Erro: {exc}\n")


def run_eval(args: argparse.Namespace) -> dict:
    """Avaliação com o índice e as críticas da amostra, carregados como no site."""
    from app.llm.compose import batch_model
    from app.rag.pipeline import Inputs, run
    from app.rag.reviews import ReviewStore
    from app.search.synopsis_index import CorpusSynopsisIndex
    from app.settings import get_settings

    settings = get_settings()
    vectors = settings.sample_vectors_dir
    index = CorpusSynopsisIndex.load(
        settings.sample_processed_dir,
        settings.sample_raw_dir,
        settings.synopsis_vectors_config,
        settings.synopsis_search_config,
        vectors=vectors if vectors.exists() else None,
    )
    reviews = ReviewStore.load(settings.sentiment_processed_dir, index.sentence_encoder())
    inputs = Inputs(
        args.questions,
        args.queries,
        args.config,
        settings.interpretation_prompt,
        settings.sample_raw_dir / "genres.json",
        settings.llm_config,
    )
    return run(inputs, args.output, index, index.titles(), reviews, lambda: batch_model(settings)[0], args.reuse, not args.without_ablation)


if __name__ == "__main__":
    raise SystemExit(main())
