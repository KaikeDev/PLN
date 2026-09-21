# 0016 — Política do `.gitignore`

- Estado: Aceita
- Data: 2026-09-21

## Contexto

O `.gitignore` explicava as próprias regras em comentários. Pela ADR 0001, justificativas ficam em ADRs, não em comentários. Além disso, algumas regras não são óbvias e, se alguém as “simplificar”, podem esconder código ou deixar passar arquivos grandes ou sensíveis:

- credenciais já foram versionadas uma vez (ADR 0002);
- os modelos pré-treinados somam cerca de 3,1 GB (ADR 0015);
- o repositório fica numa pasta do OneDrive e contém um `.docx` da entrega, o que gera arquivos temporários do Office;
- o README sugere pastas de reprodução (`reproducao`, `minha_execucao`, `nova_coleta`, `lexical`, `completo`) dentro de `data/`.

## Decisão

| Grupo | Regras | Justificativa |
|---|---|---|
| Segredos | `.env`, `.env.*`, `*.env`, `.secrets/`, `*.pem`, `*.key`; exceção `!.env.example` e `!**/.env.example` | Nenhuma credencial é versionada; só o modelo sem valores entra (ADR 0002). |
| Python | `.venv/`, `venv/`, `__pycache__/`, `*.py[cod]`, `*$py.class`, `*.egg-info/`, `.eggs/`, `build/`, `dist/`, `wheels/` | Ambientes e bytecode são recriados por `uv sync --frozen` a partir do `uv.lock`. |
| Ferramentas | `.pytest_cache/`, `.hypothesis/`, `.coverage*`, `htmlcov/`, `coverage.xml`, `.tox/`, `.nox/`, `.mypy_cache/`, `.ruff_cache/`, `.pyre/`, `.pytype/`, `.ipynb_checkpoints/` | Caches locais das ferramentas da ADR 0013 e de notebooks. |
| Modelos e caches | `.cache/`, `.hf_cache/`, `/huggingface/`, `/models/`, `*.safetensors`, `*.pt`, `*.pth`, `*.ckpt`, `*.onnx`, `*.h5`, `pytorch_model.bin` | Modelos chegam a GBs e são baixados com revisão fixada (ADR 0011). As regras evitam commits acidentais se `HF_HOME` ou uma cópia local apontar para dentro do repositório. `/huggingface/` e `/models/` são ancorados na raiz para não esconder um pacote de código como `app/models/`. |
| Dados | `data/raw/*`, `data/processed/*` e `data/vectors/*`, com exceção `!…/tmdb_2026-09-12/` em cada pasta | Só a amostra entregue é versionada (ADR 0010); reproduções locais ficam fora. |
| Front-end | `node_modules/`, `.parcel-cache/` | Reservado para o caso de ferramentas de build serem adotadas. |
| Sistema e editores | `.DS_Store`, `Thumbs.db`, `ehthumbs.db`, `desktop.ini`, `~$*`, `*.tmp`, `*.log`, `*.swp`, `*~`, `.idea/`, `.vscode/*` com exceção `!.vscode/extensions.json` | Arquivos do sistema, do OneDrive, travas do Office (`~$*.docx`) e configurações pessoais de editor; recomendações de extensões podem ser compartilhadas. |

O `.gitignore` não tem comentários: os grupos são separados por linhas em branco, na ordem da tabela acima.

## Alternativas consideradas

- **Manter os comentários no `.gitignore`:** a explicação ficaria junto da regra, mas contraria a ADR 0001 e não registra alternativas.
- **Usar o modelo genérico de `.gitignore` do GitHub para Python:** é extenso e não cobre as regras específicas do projeto (dados, modelos, ancoragem).

## Consequências

- Uma nova amostra oficial exige acrescentar a exceção em `data/*` e atualizar a tabela desta ADR.
- `git check-ignore -v <caminho>` mostra qual regra afeta um arquivo; `git ls-files -ci --exclude-standard` deve continuar vazio, ou seja, nenhum arquivo versionado pode ser ignorado.
