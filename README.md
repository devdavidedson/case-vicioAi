# Case Vicio IA — Classificação de tópicos (v2)

Sistema para decidir, em cada questão de concurso jurídico, uma de três saídas:

| Decisão | Significado |
|--------|-------------|
| **publicar** | Vai ao aluno no tema escolhido (erro mais caro se falhar) |
| **revisar** | Vai à fila do professor, com sugestão |
| **fora** | Nenhum tema da árvore serve |

**Régua do case:** das publicadas, **≥ 95%** certas. Respeitando isso, quanto mais publicar, melhor.

> **Não entregar nada à Vicio sem autorização explícita do autor deste repositório.**

---

## Branches (como usamos este repo)

| Branch | Papel |
|--------|--------|
| `caseAI_v1` | **Backup congelado** do case 1 ([case-vicioAi](https://github.com/devdavidedson/case-vicioAi)) |
| `caseAI_v2` | **Desenvolvimento** do case complementar (regras novas) |
| `main` | Espelho de `caseAI_v2` (ponto estável atual) |

```bash
git checkout caseAI_v1   # só consulta / restaura o case 1
git checkout caseAI_v2   # trabalho do dia a dia
```

---

## O que mudou do case 1 → case 2 (importante)

No case complementar:

- O modelo de linguagem **pode** (antes da decisão, documentado): embeddings, limpeza, extrair lei/artigo, enriquecer temas.
- O modelo **não pode** escolher tema, votar ou validar.
- **Na hora de classificar**, o sistema roda **sem chamar LLM**.

O pipeline em `src/pipeline.py` ainda é o da **v1** (votação com LLM). Ele fica como referência/legado. A v2 evolui para um classificador próprio (regras + busca + modelo treinado), com LLM só no pré-processamento.

---

## Requisitos

1. **Python 3.11+** (`python --version`)
2. Conta/chave **OpenAI** (humanizar relatórios; embeddings futuros)
3. Conta/chave **Jev/TypeSafe** (opcional; legado v1 e experimentos)
4. Arquivos do desafio em `dados/`: `questoes.jsonl`, `temas.csv`, `folha_verdade.csv` (quando disponível)

---

## Setup em 5 minutos

### 1) Clone / abra a pasta e entre na branch de trabalho

```bash
git checkout caseAI_v2
```

### 2) Ambiente virtual + dependências

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3) Chaves (nunca no Git)

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edite `.env` e preencha `JEV_API_KEY` e `OPENAI_API_KEY`.

### 4) Teste seco (sem gastar API de classificação)

```bash
python src/pipeline.py --demo
```

### 5) Humanizar rascunhos de relatório (OpenAI)

```bash
python -m src.humanize.cli docs/RELATORIO.md -o rascunhos/RELATORIO_humano.md
python -m src.humanize.cli relatorio.md -o rascunhos/relatorio_humano.md
```

Arquivos em `rascunhos/` são **internos**. Revisar à mão antes de qualquer envio.

---

## Pipeline de classificação (legado v1 — ainda funcional)

```bash
# teste barato
python src/pipeline.py --limite 10 --execucao teste1

# execução completa (quando dados/ estiver preenchido)
python src/pipeline.py --execucao final
```

Gera na raiz (quando não usar `--sem-entrega`):

- `publicacao.csv`
- `previsao.txt`
- `relatorio.md` (espelho de `docs/RELATORIO.md`)

Auditoria humana da amostra:

1. Preencha `correto` (S/N) em `runs/final/auditoria.csv`
2. Rode de novo o mesmo comando (usa cache)

Comparar provedores:

```bash
python src/comparar.py final
```

---

## Estrutura do projeto

```text
caseV2/
├── README.md                 ← este guia
├── pyproject.toml            ← metadados + deps modernas
├── requirements.txt          ← install rápido
├── config.json               ← provedores, limiares, regras v2
├── .env.example              ← modelo de segredos
├── publicacao.csv            ← entrega (quando gerada)
├── previsao.txt
├── relatorio.md
├── dados/                    ← anexos do case (não versionar jsonl/csv)
├── docs/
│   ├── RELATORIO.md          ← relatório técnico (fonte)
│   └── RELATORIO_INTERNO_SETUP.md
├── rascunhos/                ← textos humanizados (NÃO entregar sem ok)
├── src/
│   ├── pipeline.py           ← classificador legado v1
│   ├── auditoria.py
│   ├── comparar.py
│   └── humanize/             ← humanizador Python (StealthHumanizer → ideia)
├── tools/stealthhumanizer/   ← notas da adaptação
├── runs/final/               ← última execução versionada
└── exemplo/                  ← mini dados para --demo
```

---

## Humanização (inspirada em StealthHumanizer)

Repositório de referência: https://github.com/rudra496/StealthHumanizer

Aqui a lógica virou módulo Python (`src/humanize/`):

| Nível | O que faz | Usa API? |
|-------|-----------|----------|
| `light` | Só troca clichês locais | Não |
| `medium` | 1 passe OpenAI + regras locais | Sim |
| `aggressive` | 2 passes OpenAI + regras locais | Sim |

```bash
python -m src.humanize.cli caminho/arquivo.md -o rascunhos/saida.md --nivel medium
```

Detalhes: `tools/stealthhumanizer/NOTAS.md`.

---

## Entregáveis oficiais do case (quando autorizar o envio)

1. `publicacao.csv` — 659 linhas, formato do LEIA-ME
2. `previsao.txt` — precisão/cobertura com intervalo + método
3. Código reproduzível **sem LLM na decisão** (meta da v2)
4. Relatório ≤ 4 páginas + memo ao professor

**Status atual:** estrutura e backup prontos; classificador sem LLM na decisão ainda em evolução na `caseAI_v2`. **Nada foi enviado** à Carla/Vicio.

---

## Problemas comuns

| Sintoma | Ação |
|---------|------|
| `OPENAI_API_KEY não encontrada` | Crie `.env` a partir de `.env.example` |
| `chave JEV_API_KEY nao encontrada` | Idem para Jev |
| `Arquivo nao encontrado: dados/questoes.jsonl` | Copie os anexos do zip do case para `dados/` |
| HTTP 401 | Chave inválida/expirada — regenere no painel do provedor |
| Quero voltar ao case 1 | `git checkout caseAI_v1` |

---

## Segurança

- `.env` está no `.gitignore`
- Se uma chave apareceu em chat/e-mail, **revogue e gere outra**
- Não cole chaves no README, commits ou issues
