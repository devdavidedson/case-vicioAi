# Relatório interno — o que foi feito neste setup

> Documento **interno**. Não faz parte da entrega oficial à Vicio.
> Nada foi enviado a `carla@viciodeumaestudante.com.br`.

## Resumo

Organizamos o repositório local `caseV2` com backup do case 1, branch de desenvolvimento do case 2, humanizador de relatórios em Python (inspirado no StealthHumanizer) e README replicável. As chaves ficaram só no `.env` local.

---

## Itens feitos

### 1. Cópia do case 1 para `caseAI_v1`
- **Como:** clonamos https://github.com/devdavidedson/case-vicioAi e commitamos o conteúdo (sem o `.git` remoto).
- **Finalidade:** backup congelado da primeira entrega/teste.
- **Parte do case:** preserva o experimento de votação com LLM (pipeline v1).

### 2. Branch `caseAI_v2` + `main` como espelho
- **Como:** `caseAI_v2` criada a partir de `caseAI_v1`; desenvolvimento ocorre nela; `main` aponta para o mesmo estado da v2.
- **Finalidade:** continuar o case complementar sem perder o case 1.
- **Parte do case:** preparação para a etapa em que LLM **não** decide o tema.

### 3. Stack Python moderna
- **Como:** `pyproject.toml` + `requirements.txt` com `httpx`, `openai`, `pydantic`, `python-dotenv`, `typer`, `rich`; Python ≥ 3.11.
- **Finalidade:** base limpa, instalável e alinhada a práticas atuais.
- **Parte do case:** infraestrutura para classificação, pré-processamento e relatórios.

### 4. Humanizador (`src/humanize/`) baseado no StealthHumanizer
- **Como:** adaptamos ideias de `lib/prompts.ts` e `lib/rehumanize.ts` para Python; CLI `python -m src.humanize.cli`.
- **Finalidade:** humanizar a linguagem dos **dois** relatórios (`docs/RELATORIO.md` e `relatorio.md`) antes da revisão humana.
- **Parte do case:** melhora a qualidade de escrita do relatório/memo (critério de clareza), **sem** usar LLM para classificar questões.

### 5. Config e regras v2 documentadas
- **Como:** `config.json` ganhou provedor OpenAI e bloco `v2_regras_case` (pode / não pode).
- **Finalidade:** deixar explícito o contrato do case complementar.
- **Parte do case:** seção 4 do PDF (onde o LLM pode entrar).

### 6. README altamente organizado
- **Como:** reescrito com branches, setup, comandos, estrutura, humanização, entregáveis e troubleshooting.
- **Finalidade:** outra pessoa (ou você daqui a semanas) reproduzir o ambiente.
- **Parte do case:** requisito implícito de código/README reproduzível.

### 7. Política de não entrega
- **Como:** avisos no README, cabeçalho nos rascunhos humanizados, este relatório interno.
- **Finalidade:** cumprir “não entregue nada sem minha autorização”.
- **Parte do case:** processo interno; não altera a entrega oficial até você autorizar.

---

## O que ainda NÃO está pronto (próximos passos sugeridos)

1. Baixar `anexos-case-ia.zip` e colocar `questoes.jsonl`, `temas.csv`, `folha_verdade.csv` em `dados/`.
2. Implementar classificador v2 **sem LLM na decisão** (embeddings/regras/kNN/classificador treinado).
3. Preencher relatório real + memo ao professor com resultados.
4. Gerar `publicacao.csv` / `previsao.txt` finais e só então pedir autorização para enviar o link.

---

## Cobertura vs. PDF do case

| Exigência do PDF | Status neste setup |
|------------------|--------------------|
| Sistema que decide publicar/revisar/fora | Parcial (legado v1); v2 a construir |
| LLM só antes da decisão | Documentado; ainda não implementado no pipeline |
| Classificar sem chamar LLM | Pendente (meta da v2) |
| `publicacao.csv` + `previsao.txt` | Existem artefatos da v1; regenerar na v2 |
| Código reproduzível + README | Sim (base) |
| Relatório ≤ 4 páginas | Esqueleto + rascunhos humanizados |
| Memo professor | Ainda esqueleto dentro do relatório |
