# Adaptação do StealthHumanizer neste projeto

Fonte: https://github.com/rudra496/StealthHumanizer

## O que usamos da ideia original
- Núcleo de reescrita com preservação de significado (`lib/prompts.ts`)
- Substituições offline de clichês de IA (`lib/rehumanize.ts`)
- Multi-passe (nível medium / aggressive)
- Estilo profissional configurável

## O que NÃO embutimos
- App Next.js completo, extensão de browser, detector GPTZero, deploy Vercel
- Chaves ou proxy do mantenedor original

## Como rodamos aqui
Tudo em **Python** (`src/humanize/`), com OpenAI via `.env`, para ficar alinhado ao restante do case.

```bash
python -m src.humanize.cli docs/RELATORIO.md -o rascunhos/RELATORIO_humano.md
python -m src.humanize.cli relatorio.md -o rascunhos/relatorio_humano.md
```

Os arquivos em `rascunhos/` são **rascunhos internos**. Não entregar sem autorização.
